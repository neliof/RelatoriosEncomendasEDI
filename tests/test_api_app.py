from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from integration_app.api.app import create_app
from integration_app.models import ConnectionConfig
from integration_app.storage.sqlite_store import SQLiteStore


def test_health_endpoint_reports_database_exists(tmp_path: Path):
    db_path = tmp_path / "integration.db"
    SQLiteStore(db_path).initialize()
    app = create_app(db_path, tmp_path / "reports")

    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database_exists": True}


def test_summary_and_events_endpoints_return_json(tmp_path: Path):
    db_path = tmp_path / "integration.db"
    store = SQLiteStore(db_path)
    store.initialize()
    connection = ConnectionConfig(
        name="main",
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
    event_id = store.record_detected(connection, tmp_path / "file.txt", "/inbound/file.txt")
    app = create_app(db_path, tmp_path / "reports")
    client = TestClient(app)

    summary = client.get("/summary")
    events = client.get("/events", params={"status": "detected"})

    assert summary.status_code == 200
    assert summary.json()["total_files"] == 1
    assert events.status_code == 200
    assert events.json()["items"][0]["id"] == event_id
    assert events.json()["items"][0]["connection_name"] == "main"


def test_event_detail_endpoint_returns_enriched_json(tmp_path: Path):
    db_path = tmp_path / "integration.db"
    store = SQLiteStore(db_path)
    store.initialize()
    source = tmp_path / "send"
    sent = source / "Enviados"
    sent.mkdir(parents=True)
    file_name = "Pedido_EDI_Entregafarm_BAYER_F200-202600525.txt"
    (sent / file_name).write_text(
        "HPEDIDO0001               PT5106785059125042\n"
        "C   PT500043256                                                                                                                    2026072400010050         0001                                                                                          TER/F200/202600525\n"
        "D0000015273289             20260724\n",
        encoding="utf-8",
    )
    connection = ConnectionConfig(
        name="edi",
        enabled=True,
        flow_type="generic",
        protocol="ftp",
        host="ftp.example.test",
        port=21,
        username="user",
        source_dir=source,
        remote_dir="/inbound",
        file_pattern="*.txt",
    )
    event_id = store.record_detected(connection, source / file_name, "/inbound/" + file_name)
    instant = datetime(2026, 9, 16, 10, 0, tzinfo=UTC)
    store.record_transfer_result(event_id, "sent", instant, instant, None)
    app = create_app(db_path, tmp_path / "reports")

    response = TestClient(app).get(f"/events/{event_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == event_id
    assert payload["connection_name"] == "edi"
    assert payload["edi_fornecedor_nome"] == "BAYER"


def test_event_detail_endpoint_returns_404_for_unknown_id(tmp_path: Path):
    db_path = tmp_path / "integration.db"
    SQLiteStore(db_path).initialize()
    app = create_app(db_path, tmp_path / "reports")

    response = TestClient(app).get("/events/999")

    assert response.status_code == 404


def test_reports_endpoint_lists_files(tmp_path: Path):
    db_path = tmp_path / "integration.db"
    SQLiteStore(db_path).initialize()
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    (report_dir / "run-1-summary.csv").write_text("x", encoding="utf-8")
    app = create_app(db_path, report_dir)

    response = TestClient(app).get("/reports")

    assert response.status_code == 200
    assert response.json()["items"][0]["kind"] == "summary"


def test_report_file_endpoint_serves_existing_report(tmp_path: Path):
    db_path = tmp_path / "integration.db"
    SQLiteStore(db_path).initialize()
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    (report_dir / "run-1.csv").write_bytes(b"col\nvalue\n")
    app = create_app(db_path, report_dir)

    response = TestClient(app).get("/reports/run-1.csv")

    assert response.status_code == 200
    assert response.content == b"col\nvalue\n"
    assert "attachment" in response.headers["content-disposition"]


def test_report_file_endpoint_rejects_missing_and_unsafe_names(tmp_path: Path):
    db_path = tmp_path / "integration.db"
    SQLiteStore(db_path).initialize()
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    app = create_app(db_path, report_dir)
    client = TestClient(app)

    assert client.get("/reports/missing.csv").status_code == 404
    assert client.get("/reports/%2E%2E").status_code == 404
    assert client.get("/reports/..%2Fconfig.yaml").status_code == 404


def test_dashboard_root_serves_html_with_static_assets(tmp_path: Path):
    db_path = tmp_path / "integration.db"
    SQLiteStore(db_path).initialize()
    app = create_app(db_path, tmp_path / "reports")

    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Relatorios Encomendas EDI EF" in response.text
    assert "/static/dashboard.css" in response.text
    assert "/static/dashboard.js" in response.text


def test_dashboard_static_assets_are_served(tmp_path: Path):
    db_path = tmp_path / "integration.db"
    SQLiteStore(db_path).initialize()
    app = create_app(db_path, tmp_path / "reports")
    client = TestClient(app)

    css = client.get("/static/dashboard.css")
    js = client.get("/static/dashboard.js")

    assert css.status_code == 200
    assert "text/css" in css.headers["content-type"]
    assert ".metric-card" in css.text
    assert js.status_code == 200
    assert "text/javascript" in js.headers["content-type"]
    assert "fetchSummary" in js.text


def test_dashboard_html_contains_required_dom_hooks(tmp_path: Path):
    db_path = tmp_path / "integration.db"
    SQLiteStore(db_path).initialize()
    app = create_app(db_path, tmp_path / "reports")

    html = TestClient(app).get("/").text

    required_ids = [
        "last-updated",
        "refresh-button",
        "metric-total",
        "metric-sent",
        "metric-confirmed",
        "metric-pending",
        "metric-duplicate",
        "metric-failed",
        "event-filters",
        "status-filter",
        "connection-filter",
        "date-from-filter",
        "date-to-filter",
        "limit-filter",
        "operational-alerts",
        "events-body",
        "event-detail",
        "event-detail-body",
        "event-detail-close",
        "suppliers-list",
        "reports-list",
    ]
    for element_id in required_ids:
        assert f'id="{element_id}"' in html


def test_dashboard_javascript_uses_existing_readonly_endpoints(tmp_path: Path):
    db_path = tmp_path / "integration.db"
    SQLiteStore(db_path).initialize()
    app = create_app(db_path, tmp_path / "reports")

    javascript = TestClient(app).get("/static/dashboard.js").text

    assert 'getJson("/summary")' in javascript
    assert "getJson(`/events?" in javascript
    assert 'params.set("date_from", dateFrom)' in javascript
    assert 'params.set("date_to", dateTo)' in javascript
    assert 'getJson("/suppliers")' in javascript
    assert 'getJson("/reports")' in javascript
    assert 'href = `/reports/${encodeURIComponent(report.name || "")}`' in javascript
    assert "showEventDetail" in javascript
    assert "getJson(`/events/${eventId}`)" in javascript
    assert "fetch(" in javascript
    assert "method:" not in javascript


def test_dashboard_assets_include_operational_alert_styles(tmp_path: Path):
    db_path = tmp_path / "integration.db"
    SQLiteStore(db_path).initialize()
    app = create_app(db_path, tmp_path / "reports")

    css = TestClient(app).get("/static/dashboard.css").text
    javascript = TestClient(app).get("/static/dashboard.js").text

    assert ".alerts" in css
    assert ".alert-item.failed" in css
    assert "renderOperationalAlerts" in javascript
    assert "failed_count" in javascript
    assert "duplicate_count" in javascript
    assert "pending_count" in javascript
