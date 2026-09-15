from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Callable

from integration_app.core.files import discover_files, is_stable, move_to_status_dir, remote_path_for
from integration_app.models import AppConfig, ConnectionConfig
from integration_app.order_edi import order_duplicate_key, parse_order_edi_file
from integration_app.order_xml import order_xml_duplicate_key, parse_order_xml_file
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
            is_duplicate = _is_duplicate_order(connection, store, local_path)
            event_id = store.record_detected(connection, local_path, remote_path)
            started = datetime.now(UTC)
            if is_duplicate:
                try:
                    move_to_status_dir(local_path, "Duplicados")
                    finished = datetime.now(UTC)
                    store.record_transfer_result(event_id, "duplicate", started, finished, "Duplicate order EDI")
                except Exception as exc:
                    finished = datetime.now(UTC)
                    store.record_transfer_result(event_id, "failed", started, finished, str(exc))
                    summary = summary.add(processed=1, failed=1)
                    continue
                summary = summary.add(processed=1)
                continue
            client: TransferClient | None = None
            try:
                client = client_factory(connection)
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
                if client is not None:
                    _close_defensively(client)
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
    client: TransferClient | None = None
    try:
        client = client_factory(connection)
        client.connect()
        for item in pending:
            checked_at = datetime.now(UTC)
            if not client.exists(item.remote_path):
                store.record_confirmation(item.event_id, "confirmed", checked_at)
                summary = summary.add(confirmed=1)
            elif checked_at - item.sent_at > timedelta(minutes=config.defaults.confirmation_timeout_minutes):
                store.record_confirmation(item.event_id, "confirmation_timeout", checked_at)
                summary = summary.add(confirmation_timeouts=1)
    except Exception:
        return summary
    finally:
        if client is not None:
            _close_defensively(client)
    return summary


def _close_defensively(client: TransferClient) -> None:
    with suppress(Exception):
        client.close()


def _is_duplicate_order(connection: ConnectionConfig, store: SQLiteStore, local_path: Path) -> bool:
    if connection.duplicate_policy != "move_to_duplicates":
        return False
    current_key = _file_duplicate_key(local_path)
    if current_key is None:
        return False
    for row in store.report_rows():
        if row.get("connection_name") != connection.name:
            continue
        existing_path = _resolve_existing_order_path(row)
        if existing_path is None:
            continue
        if _file_duplicate_key(existing_path) == current_key:
            return True
    return False


def _file_duplicate_key(path: Path) -> str | None:
    try:
        if path.suffix.lower() == ".xml":
            key = order_xml_duplicate_key(parse_order_xml_file(path))
            return f"xml:{key}" if key is not None else None
        key = order_duplicate_key(parse_order_edi_file(path))
        return f"edi:{key}" if key is not None else None
    except Exception:
        return None


def _resolve_existing_order_path(row: dict[str, object]) -> Path | None:
    local_path = row.get("local_path")
    if not isinstance(local_path, str):
        return None
    path = Path(local_path)
    status = row.get("status")
    if status not in {"sent", "confirmed", "duplicate"}:
        return None
    if path.exists():
        return path
    sent_path = path.parent / "Enviados" / path.name
    if sent_path.exists():
        return sent_path
    duplicate_path = path.parent / "Duplicados" / path.name
    if duplicate_path.exists():
        return duplicate_path
    return None
