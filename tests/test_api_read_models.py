from datetime import UTC, datetime
from pathlib import Path

from integration_app.api.read_models import EventFilters, fetch_events, fetch_summary
from integration_app.models import ConnectionConfig
from integration_app.storage.sqlite_store import SQLiteStore


def _connection(tmp_path: Path, name: str = "main") -> ConnectionConfig:
    return ConnectionConfig(
        name=name,
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


def test_fetch_summary_counts_file_statuses(tmp_path: Path):
    store = SQLiteStore(tmp_path / "integration.db")
    store.initialize()
    connection = _connection(tmp_path)
    instant = datetime(2026, 9, 16, 10, 0, tzinfo=UTC)

    sent_id = store.record_detected(connection, tmp_path / "sent.txt", "/inbound/sent.txt")
    store.record_transfer_result(sent_id, "sent", instant, instant, None)
    confirmed_id = store.record_detected(connection, tmp_path / "confirmed.txt", "/inbound/confirmed.txt")
    store.record_transfer_result(confirmed_id, "sent", instant, instant, None)
    store.record_confirmation(confirmed_id, "confirmed", instant)
    duplicate_id = store.record_detected(connection, tmp_path / "dup.txt", "/inbound/dup.txt")
    store.record_transfer_result(duplicate_id, "duplicate", instant, instant, "Duplicate")
    failed_id = store.record_detected(connection, tmp_path / "bad.txt", "/inbound/bad.txt")
    store.record_transfer_result(failed_id, "failed", instant, instant, "Boom")

    summary = fetch_summary(tmp_path / "integration.db")

    assert summary["total_files"] == 4
    assert summary["sent_count"] == 2
    assert summary["confirmed_count"] == 1
    assert summary["duplicate_count"] == 1
    assert summary["failed_count"] == 1
    assert summary["pending_count"] == 1
    assert summary["unknown_count"] == 0
    assert summary["last_detected_at"]


def test_fetch_events_filters_by_status_connection_and_date(tmp_path: Path):
    store = SQLiteStore(tmp_path / "integration.db")
    store.initialize()
    connection = _connection(tmp_path, "edi")
    instant = datetime(2026, 9, 16, 10, 0, tzinfo=UTC)
    event_id = store.record_detected(connection, tmp_path / "file.txt", "/inbound/file.txt")
    store.record_transfer_result(event_id, "failed", instant, instant, "Boom")

    rows = fetch_events(
        tmp_path / "integration.db",
        EventFilters(status="failed", connection_name="edi", date_from="2026-09-16", date_to="2026-09-16", limit=10),
    )

    assert len(rows) == 1
    assert rows[0]["connection_name"] == "edi"
    assert rows[0]["status"] == "failed"
    assert rows[0]["error_message"] == "Boom"
