from datetime import UTC, datetime
from pathlib import Path

from integration_app.api.read_models import (
    EventFilters,
    fetch_connections,
    fetch_event_detail,
    fetch_events,
    fetch_summary,
    fetch_suppliers,
    list_reports,
)
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
    assert rows[0]["id"] == event_id
    assert rows[0]["status"] == "failed"
    assert rows[0]["error_message"] == "Boom"


def test_fetch_event_detail_returns_enriched_order_fields(tmp_path: Path):
    store = SQLiteStore(tmp_path / "integration.db")
    store.initialize()
    source = tmp_path / "send"
    sent = source / "Enviados"
    sent.mkdir(parents=True)
    connection = _connection(source, "edi")
    file_name = "Pedido_EDI_Entregafarm_BAYER_F200-202600525.txt"
    (sent / file_name).write_text(
        "HPEDIDO0001               PT5106785059125042\n"
        "C   PT500043256                                                                                                                    2026072400010050         0001                                                                                          TER/F200/202600525\n"
        "D0000015273289             20260724\n",
        encoding="utf-8",
    )
    instant = datetime(2026, 9, 16, 10, 0, tzinfo=UTC)
    event_id = store.record_detected(connection, source / file_name, "/inbound/" + file_name)
    store.record_transfer_result(event_id, "sent", instant, instant, None)

    detail = fetch_event_detail(tmp_path / "integration.db", event_id)

    assert detail is not None
    assert detail["id"] == event_id
    assert detail["connection_name"] == "edi"
    assert detail["edi_fornecedor_nome"] == "BAYER"
    assert detail["edi_numero_encomenda"] == "202600525"
    assert detail["edi_duplicate_key"]


def test_fetch_events_includes_enriched_supplier_and_order_fields(tmp_path: Path):
    store = SQLiteStore(tmp_path / "integration.db")
    store.initialize()
    source = tmp_path / "send"
    sent = source / "Enviados"
    sent.mkdir(parents=True)
    connection = _connection(source, "edi")
    file_name = "Pedido_EDI_Entregafarm_BAYER_F200-202600525.txt"
    (sent / file_name).write_text(
        "HPEDIDO0001               PT5106785059125042\n"
        "C   PT500043256                                                                                                                    2026072400010050         0001                                                                                          TER/F200/202600525\n"
        "D0000015273289             20260724\n",
        encoding="utf-8",
    )
    instant = datetime(2026, 9, 16, 10, 0, tzinfo=UTC)
    event_id = store.record_detected(connection, source / file_name, "/inbound/" + file_name)
    store.record_transfer_result(event_id, "sent", instant, instant, None)

    rows = fetch_events(tmp_path / "integration.db", EventFilters(limit=10))

    assert rows[0]["id"] == event_id
    assert rows[0]["edi_fornecedor_nome"] == "BAYER"
    assert rows[0]["edi_numero_encomenda"] == "202600525"


def test_fetch_connections_aggregates_status_by_connection(tmp_path: Path):
    store = SQLiteStore(tmp_path / "integration.db")
    store.initialize()
    edi = _connection(tmp_path, "edi")
    xml = _connection(tmp_path, "xml")
    instant = datetime(2026, 9, 16, 10, 0, tzinfo=UTC)
    sent_id = store.record_detected(edi, tmp_path / "sent.txt", "/inbound/sent.txt")
    store.record_transfer_result(sent_id, "sent", instant, instant, None)
    failed_id = store.record_detected(edi, tmp_path / "failed.txt", "/inbound/failed.txt")
    store.record_transfer_result(failed_id, "failed", instant, instant, "Boom")
    duplicate_id = store.record_detected(xml, tmp_path / "duplicate.xml", "/inbound/duplicate.xml")
    store.record_transfer_result(duplicate_id, "duplicate", instant, instant, "Duplicate")

    rows = fetch_connections(tmp_path / "integration.db")

    assert rows == [
        {
            "connection_name": "edi",
            "protocol": "ftp",
            "total_files": 2,
            "sent_count": 1,
            "confirmed_count": 0,
            "duplicate_count": 0,
            "failed_count": 1,
            "pending_count": 1,
            "last_detected_at": rows[0]["last_detected_at"],
        },
        {
            "connection_name": "xml",
            "protocol": "ftp",
            "total_files": 1,
            "sent_count": 0,
            "confirmed_count": 0,
            "duplicate_count": 1,
            "failed_count": 0,
            "pending_count": 0,
            "last_detected_at": rows[1]["last_detected_at"],
        },
    ]


def test_fetch_event_detail_returns_none_for_unknown_id(tmp_path: Path):
    store = SQLiteStore(tmp_path / "integration.db")
    store.initialize()

    assert fetch_event_detail(tmp_path / "integration.db", 999) is None


def test_list_reports_classifies_report_files(tmp_path: Path):
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    (report_dir / "run-20260916-090101-summary.csv").write_text("x", encoding="utf-8")
    (report_dir / "generix-20260916-090101-exceptions.json").write_text("x", encoding="utf-8")
    (report_dir / "run-20260916-090101.csv").write_text("x", encoding="utf-8")

    rows = list_reports(report_dir)

    rows_by_name = {row["name"]: row for row in rows}
    assert rows_by_name["run-20260916-090101-summary.csv"]["kind"] == "summary"
    assert rows_by_name["generix-20260916-090101-exceptions.json"]["kind"] == "generix_exceptions"
    assert rows_by_name["run-20260916-090101.csv"]["kind"] == "run"


def test_fetch_suppliers_uses_filename_supplier_for_known_edi_orders(tmp_path: Path):
    store = SQLiteStore(tmp_path / "integration.db")
    store.initialize()
    source = tmp_path / "send"
    sent = source / "Enviados"
    sent.mkdir(parents=True)
    connection = _connection(source, "edi")
    file_name = "Pedido_EDI_Entregafarm_BAYER_F200-202600525.txt"
    (sent / file_name).write_text(
        "HPEDIDO0001               PT5106785059125042\n"
        "C   PT500043256                                                                                                                    2026072400010050         0001                                                                                          TER/F200/202600525\n"
        "D0000015273289             20260724\n",
        encoding="utf-8",
    )
    instant = datetime(2026, 9, 16, 10, 0, tzinfo=UTC)
    event_id = store.record_detected(connection, source / file_name, "/inbound/" + file_name)
    store.record_transfer_result(event_id, "sent", instant, instant, None)
    store.record_confirmation(event_id, "confirmed", instant)

    suppliers = fetch_suppliers(tmp_path / "integration.db")

    assert suppliers == [
        {
            "supplier_name": "BAYER",
            "total_files": 1,
            "failed_count": 0,
            "duplicate_count": 0,
        }
    ]
