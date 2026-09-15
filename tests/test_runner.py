import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from integration_app.core.runner import run_once
from integration_app.models import AppConfig, AppPaths, ConnectionConfig, DefaultsConfig
from integration_app.storage.sqlite_store import SQLiteStore


class FakeClient:
    def __init__(
        self,
        *,
        upload_error: Exception | None = None,
        exists_error: Exception | None = None,
        close_error: Exception | None = None,
    ):
        self.uploaded = []
        self.remote_exists = False
        self.upload_error = upload_error
        self.exists_error = exists_error
        self.close_error = close_error

    def connect(self):
        return None

    def upload(self, local_path: Path, remote_path: str):
        if self.upload_error is not None:
            raise self.upload_error
        self.uploaded.append((local_path, remote_path))

    def exists(self, remote_path: str) -> bool:
        if self.exists_error is not None:
            raise self.exists_error
        return self.remote_exists

    def close(self):
        if self.close_error is not None:
            raise self.close_error
        return None


def make_config(
    tmp_path: Path,
    connections: list[ConnectionConfig],
    *,
    stable_after_seconds: int = 0,
    confirmation_timeout_minutes: int = 120,
) -> AppConfig:
    return AppConfig(
        app=AppPaths(tmp_path / "data" / "integration.db", tmp_path / "logs", tmp_path / "reports"),
        defaults=DefaultsConfig(
            stable_after_seconds=stable_after_seconds,
            confirmation_timeout_minutes=confirmation_timeout_minutes,
        ),
        connections=connections,
    )


def make_connection(
    source: Path,
    *,
    name: str = "lab",
    enabled: bool = True,
    remote_dir: str = "/inbound",
    file_pattern: str = "*.edi",
    duplicate_policy: str = "report_only",
) -> ConnectionConfig:
    return ConnectionConfig(
        name=name,
        enabled=enabled,
        flow_type="generic",
        protocol="ftp",
        host=f"{name}.example.test",
        port=21,
        username="user",
        source_dir=source,
        remote_dir=remote_dir,
        file_pattern=file_pattern,
        duplicate_policy=duplicate_policy,
    )


def initialized_store(config: AppConfig) -> SQLiteStore:
    store = SQLiteStore(config.app.database_path)
    store.initialize()
    return store


def test_run_once_uploads_stable_file_and_moves_to_sent(tmp_path: Path):
    source = tmp_path / "inbox"
    source.mkdir()
    file_path = source / "order.edi"
    file_path.write_text("EDI", encoding="utf-8")

    config = make_config(tmp_path, [make_connection(source)])
    store = initialized_store(config)
    fake = FakeClient()

    summary = run_once(config, store, client_factory=lambda connection: fake)

    assert summary.sent == 1
    assert fake.uploaded == [(file_path, "/inbound/order.edi")]
    assert (source / "Enviados" / "order.edi").exists()


def test_run_once_moves_failed_upload_to_errors(tmp_path: Path):
    source = tmp_path / "inbox"
    source.mkdir()
    file_path = source / "order.edi"
    file_path.write_text("EDI", encoding="utf-8")

    config = make_config(tmp_path, [make_connection(source)])
    store = initialized_store(config)
    fake = FakeClient(upload_error=RuntimeError("upload failed"))

    summary = run_once(config, store, client_factory=lambda connection: fake)

    assert summary.failed == 1
    assert summary.sent == 0
    assert (source / "Erros" / "order.edi").exists()


def test_run_once_skips_unstable_file(tmp_path: Path):
    source = tmp_path / "inbox"
    source.mkdir()
    file_path = source / "order.edi"
    file_path.write_text("EDI", encoding="utf-8")
    current_timestamp = datetime.now(UTC).timestamp()
    os.utime(file_path, (current_timestamp, current_timestamp))

    config = make_config(tmp_path, [make_connection(source)], stable_after_seconds=3600)
    store = initialized_store(config)
    fake = FakeClient()

    summary = run_once(config, store, client_factory=lambda connection: fake)

    assert summary.skipped_unstable == 1
    assert summary.processed == 0
    assert fake.uploaded == []
    assert file_path.exists()


def test_run_once_skips_inactive_connection(tmp_path: Path):
    source = tmp_path / "inbox"
    source.mkdir()
    file_path = source / "order.edi"
    file_path.write_text("EDI", encoding="utf-8")

    config = make_config(tmp_path, [make_connection(source, enabled=False)])
    store = initialized_store(config)
    fake = FakeClient()

    summary = run_once(config, store, client_factory=lambda connection: fake)

    assert summary == summary.__class__()
    assert fake.uploaded == []
    assert file_path.exists()


def test_run_once_confirms_pending_file_when_remote_disappears(tmp_path: Path):
    source = tmp_path / "inbox"
    source.mkdir()
    connection = make_connection(source)
    config = make_config(tmp_path, [connection])
    store = initialized_store(config)
    event_id = store.record_detected(connection, source / "order.edi", "/inbound/order.edi")
    now = datetime.now(UTC)
    store.record_transfer_result(event_id, "sent", now, now, None)
    fake = FakeClient()
    fake.remote_exists = False

    summary = run_once(config, store, client_factory=lambda connection: fake)

    assert summary.confirmed == 1
    assert store.pending_confirmations() == []


def test_run_once_marks_pending_confirmation_timeout(tmp_path: Path):
    source = tmp_path / "inbox"
    source.mkdir()
    connection = make_connection(source)
    config = make_config(tmp_path, [connection], confirmation_timeout_minutes=1)
    store = initialized_store(config)
    event_id = store.record_detected(connection, source / "order.edi", "/inbound/order.edi")
    old_sent_at = datetime.now(UTC) - timedelta(minutes=5)
    store.record_transfer_result(event_id, "sent", old_sent_at, old_sent_at, None)
    fake = FakeClient()
    fake.remote_exists = True

    summary = run_once(config, store, client_factory=lambda connection: fake)

    assert summary.confirmation_timeouts == 1
    assert store.pending_confirmations() == []


def test_run_once_records_factory_failure_and_continues_to_later_connection(tmp_path: Path):
    failing_source = tmp_path / "failing"
    succeeding_source = tmp_path / "succeeding"
    failing_source.mkdir()
    succeeding_source.mkdir()
    failing_file = failing_source / "bad.edi"
    succeeding_file = succeeding_source / "good.edi"
    failing_file.write_text("BAD", encoding="utf-8")
    succeeding_file.write_text("GOOD", encoding="utf-8")
    failing = make_connection(failing_source, name="failing")
    succeeding = make_connection(succeeding_source, name="succeeding")
    config = make_config(tmp_path, [failing, succeeding])
    store = initialized_store(config)
    succeeding_client = FakeClient()

    def client_factory(connection: ConnectionConfig) -> FakeClient:
        if connection.name == "failing":
            raise RuntimeError("factory failed")
        return succeeding_client

    summary = run_once(config, store, client_factory=client_factory)

    assert summary.failed == 1
    assert summary.sent == 1
    assert (failing_source / "Erros" / "bad.edi").exists()
    assert (succeeding_source / "Enviados" / "good.edi").exists()


def test_run_once_ignores_close_failure_after_success(tmp_path: Path):
    source = tmp_path / "inbox"
    source.mkdir()
    file_path = source / "order.edi"
    file_path.write_text("EDI", encoding="utf-8")

    config = make_config(tmp_path, [make_connection(source)])
    store = initialized_store(config)
    fake = FakeClient(close_error=RuntimeError("close failed"))

    summary = run_once(config, store, client_factory=lambda connection: fake)

    assert summary.sent == 1
    assert (source / "Enviados" / "order.edi").exists()


def test_run_once_continues_when_confirmation_check_fails_for_one_connection(tmp_path: Path):
    failing_source = tmp_path / "failing"
    succeeding_source = tmp_path / "succeeding"
    failing_source.mkdir()
    succeeding_source.mkdir()
    succeeding_file = succeeding_source / "good.edi"
    succeeding_file.write_text("GOOD", encoding="utf-8")
    failing = make_connection(failing_source, name="failing")
    succeeding = make_connection(succeeding_source, name="succeeding")
    config = make_config(tmp_path, [failing, succeeding])
    store = initialized_store(config)
    event_id = store.record_detected(failing, failing_source / "old.edi", "/inbound/old.edi")
    sent_at = datetime.now(UTC)
    store.record_transfer_result(event_id, "sent", sent_at, sent_at, None)
    clients = {
        "failing": FakeClient(exists_error=RuntimeError("exists failed")),
        "succeeding": FakeClient(),
    }

    summary = run_once(config, store, client_factory=lambda connection: clients[connection.name])

    assert summary.sent == 1
    assert (succeeding_source / "Enviados" / "good.edi").exists()


def test_run_once_moves_duplicate_order_to_duplicates_without_upload(tmp_path: Path):
    source = tmp_path / "send"
    sent = source / "Enviados"
    source.mkdir()
    sent.mkdir()
    file_name = "Pedido_EDI_Entregafarm_BAYER_F200-202600525.txt"
    order_content = """HPEDIDO0001               PT5106785059125042
C   PT500043256                                                                                                                    2026072400010050         0001                                                                                          TER/F200/202600525
D0000015273289             20260724
"""
    (sent / file_name).write_text(order_content, encoding="utf-8")
    new_file = source / file_name
    new_file.write_text(order_content, encoding="utf-8")
    connection = make_connection(source, file_pattern="*.txt", duplicate_policy="move_to_duplicates")
    config = make_config(tmp_path, [connection])
    store = initialized_store(config)
    previous_id = store.record_detected(connection, source / file_name, "/inbound/" + file_name)
    instant = datetime(2026, 9, 14, 10, 0, tzinfo=UTC)
    store.record_transfer_result(previous_id, "sent", instant, instant, None)
    store.record_confirmation(previous_id, "confirmed", instant)
    fake = FakeClient()

    summary = run_once(config, store, client_factory=lambda connection: fake)

    assert summary.processed == 1
    assert summary.sent == 0
    assert summary.failed == 0
    assert fake.uploaded == []
    assert (source / "Duplicados" / file_name).exists()
    rows = store.report_rows()
    assert rows[-1]["status"] == "duplicate"
