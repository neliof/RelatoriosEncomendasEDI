from datetime import UTC, datetime
from pathlib import Path

from integration_app.models import ConnectionConfig
from integration_app.reports.exporters import export_reports
from integration_app.storage.sqlite_store import SQLiteStore


def test_export_reports_writes_csv_json_and_xlsx(tmp_path: Path):
    store = SQLiteStore(tmp_path / "integration.db")
    store.initialize()
    connection = ConnectionConfig(
        name="lab",
        enabled=True,
        flow_type="generic",
        protocol="ftp",
        host="ftp.example.test",
        port=21,
        username="user",
        source_dir=tmp_path,
        remote_dir="/inbound",
        file_pattern="*.edi",
    )
    event_id = store.record_detected(connection, tmp_path / "order.edi", "/inbound/order.edi")
    instant = datetime(2026, 9, 14, 10, 0, tzinfo=UTC)
    store.record_transfer_result(event_id, "sent", instant, instant, None)

    paths = export_reports(store, tmp_path / "reports", "run-1")

    names = {path.name for path in paths}
    assert names == {"run-1.csv", "run-1.json", "run-1.xlsx"}
    assert (tmp_path / "reports" / "run-1.csv").read_text(encoding="utf-8").startswith("connection_name,")
