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


def test_export_reports_enriches_sent_order_edi_from_status_folder(tmp_path: Path):
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
        file_pattern="*.txt",
    )
    file_name = "Pedido_EDI_Entregafarm_BAYER_F200-202600525.txt"
    original_path = tmp_path / file_name
    sent_path = tmp_path / "Enviados" / file_name
    sent_path.parent.mkdir()
    sent_path.write_text(
        """HPEDIDO0001               PT5106785059125042
C   PT500043256                                                                                                                    2026072400010050         0001                                                                                          TER/F200/202600525
D0000015273289             20260724
D0000023045580             20260724
""",
        encoding="utf-8",
    )
    event_id = store.record_detected(connection, original_path, "/inbound/" + file_name)
    instant = datetime(2026, 9, 14, 10, 0, tzinfo=UTC)
    store.record_transfer_result(event_id, "sent", instant, instant, None)
    store.record_confirmation(event_id, "confirmed", instant)

    export_reports(store, tmp_path / "reports", "run-edi")

    csv_text = (tmp_path / "reports" / "run-edi.csv").read_text(encoding="utf-8")
    assert "edi_tipo_mensagem" in csv_text
    assert "HPEDIDO0001" in csv_text
    assert "Entregafarm" in csv_text
    assert "BAYER" in csv_text
    assert "TER/F200/202600525" in csv_text
