from datetime import UTC, datetime
from pathlib import Path

from integration_app.models import ConnectionConfig
from integration_app.storage.sqlite_store import SQLiteStore


def _connection(tmp_path: Path) -> ConnectionConfig:
    return ConnectionConfig(
        name="lab",
        enabled=True,
        flow_type="generic",
        protocol="ftp",
        host="ftp.example.test",
        port=21,
        username="user",
        source_dir=tmp_path,
        remote_dir="/inbound",
        file_pattern="*.txt",
    )


def test_records_file_lifecycle(tmp_path: Path):
    store = SQLiteStore(tmp_path / "integration.db")
    store.initialize()
    connection = _connection(tmp_path)

    event_id = store.record_detected(connection, tmp_path / "a.txt", "/inbound/a.txt")
    started = datetime(2026, 9, 14, 10, 0, tzinfo=UTC)
    finished = datetime(2026, 9, 14, 10, 1, tzinfo=UTC)
    store.record_transfer_result(event_id, "sent", started, finished, None)
    pending = store.pending_confirmations()

    assert len(pending) == 1
    assert pending[0].event_id == event_id
    assert pending[0].remote_path == "/inbound/a.txt"

    store.record_confirmation(event_id, "confirmed", finished)
    assert store.pending_confirmations() == []
