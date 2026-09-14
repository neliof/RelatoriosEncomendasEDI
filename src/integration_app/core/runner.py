from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Callable

from integration_app.core.files import discover_files, is_stable, move_to_status_dir, remote_path_for
from integration_app.models import AppConfig, ConnectionConfig
from integration_app.storage.sqlite_store import SQLiteStore
from integration_app.transfers.base import TransferClient, build_transfer_client


@dataclass(frozen=True)
class RunSummary:
    processed: int = 0
    sent: int = 0
    failed: int = 0
    skipped_unstable: int = 0
    confirmed: int = 0
    confirmation_timeouts: int = 0

    def add(self, **changes: int) -> "RunSummary":
        values = self.__dict__.copy()
        for key, value in changes.items():
            values[key] += value
        return RunSummary(**values)


def run_once(
    config: AppConfig,
    store: SQLiteStore,
    client_factory: Callable[[ConnectionConfig], TransferClient] = build_transfer_client,
) -> RunSummary:
    summary = RunSummary()
    enabled = [connection for connection in config.connections if connection.enabled]
    for connection in enabled:
        summary = _check_pending_confirmations(config, store, connection, client_factory, summary)
        for local_path in discover_files(connection):
            if not is_stable(local_path, config.defaults.stable_after_seconds):
                summary = summary.add(skipped_unstable=1)
                continue
            remote_path = remote_path_for(connection, local_path)
            event_id = store.record_detected(connection, local_path, remote_path)
            started = datetime.now(UTC)
            client = client_factory(connection)
            try:
                client.connect()
                client.upload(local_path, remote_path)
                finished = datetime.now(UTC)
                store.record_transfer_result(event_id, "sent", started, finished, None)
                move_to_status_dir(local_path, connection.sent_dir)
                summary = summary.add(processed=1, sent=1)
            except Exception as exc:
                finished = datetime.now(UTC)
                store.record_transfer_result(event_id, "failed", started, finished, str(exc))
                if local_path.exists():
                    move_to_status_dir(local_path, connection.error_dir)
                summary = summary.add(processed=1, failed=1)
            finally:
                client.close()
    return summary


def _check_pending_confirmations(
    config: AppConfig,
    store: SQLiteStore,
    connection: ConnectionConfig,
    client_factory: Callable[[ConnectionConfig], TransferClient],
    summary: RunSummary,
) -> RunSummary:
    pending = [item for item in store.pending_confirmations() if item.connection_name == connection.name]
    if not pending:
        return summary
    client = client_factory(connection)
    try:
        client.connect()
        for item in pending:
            checked_at = datetime.now(UTC)
            if not client.exists(item.remote_path):
                store.record_confirmation(item.event_id, "confirmed", checked_at)
                summary = summary.add(confirmed=1)
            elif checked_at - item.sent_at > timedelta(minutes=config.defaults.confirmation_timeout_minutes):
                store.record_confirmation(item.event_id, "confirmation_timeout", checked_at)
                summary = summary.add(confirmation_timeouts=1)
    finally:
        client.close()
    return summary
