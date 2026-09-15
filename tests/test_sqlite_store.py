import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

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


def test_failed_transfer_is_not_left_pending_confirmation(tmp_path: Path):
    store = SQLiteStore(tmp_path / "integration.db")
    store.initialize()
    connection = _connection(tmp_path)
    event_id = store.record_detected(connection, tmp_path / "a.txt", "/inbound/a.txt")
    started = datetime(2026, 9, 14, 10, 0, tzinfo=UTC)
    finished = datetime(2026, 9, 14, 10, 1, tzinfo=UTC)

    store.record_transfer_result(event_id, "failed", started, finished, "upload failed")

    rows = store.report_rows()
    assert rows[0]["status"] == "failed"
    assert rows[0]["confirmation_status"] == "failed"
    assert store.pending_confirmations() == []


def test_duplicate_transfer_is_skipped_for_remote_confirmation(tmp_path: Path):
    store = SQLiteStore(tmp_path / "integration.db")
    store.initialize()
    connection = _connection(tmp_path)
    event_id = store.record_detected(connection, tmp_path / "a.txt", "/inbound/a.txt")
    started = datetime(2026, 9, 14, 10, 0, tzinfo=UTC)
    finished = datetime(2026, 9, 14, 10, 1, tzinfo=UTC)

    store.record_transfer_result(event_id, "duplicate", started, finished, "Duplicate order EDI")

    rows = store.report_rows()
    assert rows[0]["status"] == "duplicate"
    assert rows[0]["confirmation_status"] == "skipped"
    assert store.pending_confirmations() == []


def test_initialize_migrates_terminal_transfers_away_from_pending(tmp_path: Path):
    db_path = tmp_path / "integration.db"
    store = SQLiteStore(db_path)
    store.initialize()
    connection = _connection(tmp_path)
    failed_id = store.record_detected(connection, tmp_path / "failed.txt", "/inbound/failed.txt")
    duplicate_id = store.record_detected(connection, tmp_path / "duplicate.txt", "/inbound/duplicate.txt")

    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE file_events SET status = 'failed', confirmation_status = 'pending' WHERE id = ?", (failed_id,))
        conn.execute(
            "UPDATE file_events SET status = 'duplicate', confirmation_status = 'pending' WHERE id = ?",
            (duplicate_id,),
        )

    store.initialize()

    rows = store.report_rows()
    assert rows[0]["confirmation_status"] == "failed"
    assert rows[1]["confirmation_status"] == "skipped"


def test_rejects_transfer_result_for_unknown_event(tmp_path: Path):
    store = SQLiteStore(tmp_path / "integration.db")
    store.initialize()
    started = datetime(2026, 9, 14, 10, 0, tzinfo=UTC)
    finished = datetime(2026, 9, 14, 10, 1, tzinfo=UTC)

    with pytest.raises(sqlite3.IntegrityError):
        store.record_transfer_result(999, "sent", started, finished, None)
