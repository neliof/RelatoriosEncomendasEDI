# Backend Local Read-Only Dashboard API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local read-only HTTP API for monitoring integration events, summaries, suppliers and generated reports.

**Architecture:** Add a focused `integration_app.api` package. `read_models.py` contains pure read-only SQLite/report-folder queries; `app.py` exposes FastAPI endpoints; `__main__.py` starts Uvicorn locally. The API does not import FTP/SFTP clients, does not read secrets, and does not write to the database.

**Tech Stack:** Python 3.11+, FastAPI, Uvicorn, SQLite, pytest, FastAPI TestClient.

**Spec:** `docs/superpowers/specs/2026-09-16-backend-local-readonly-dashboard-api-design.md`

## Global Constraints

- API is local and read-only.
- Default host is `127.0.0.1`.
- Default port is `8000`.
- Default database path is `data/integration.db`.
- Default reports path is `reports`.
- Do not alter FTP/SFTP transfer behaviour.
- Do not alter Task Scheduler.
- Do not expose passwords, `secrets/`, or raw `config.yaml` contents.
- Use TDD for implementation changes.

---

## File Structure

- Create `src/integration_app/api/__init__.py`: package marker.
- Create `src/integration_app/api/read_models.py`: read-only query and aggregation functions.
- Create `src/integration_app/api/app.py`: FastAPI app factory and endpoint definitions.
- Create `src/integration_app/api/__main__.py`: CLI entry point using Uvicorn.
- Modify `pyproject.toml`: add `fastapi` and `uvicorn` dependencies.
- Modify `README.md` or `docs/install-windows-task-scheduler.md`: document local API command.
- Create `tests/test_api_read_models.py`: tests for pure read-model functions.
- Create `tests/test_api_app.py`: endpoint tests with TestClient.

---

### Task 1: Add Read-Only Event Queries And Summary Aggregation

**Files:**
- Create: `src/integration_app/api/__init__.py`
- Create: `src/integration_app/api/read_models.py`
- Test: `tests/test_api_read_models.py`

**Interfaces:**
- Produces: `fetch_events(db_path: Path, filters: EventFilters) -> list[dict[str, object]]`
- Produces: `fetch_summary(db_path: Path) -> dict[str, object]`
- Produces: `EventFilters(status: str | None = None, connection_name: str | None = None, date_from: str | None = None, date_to: str | None = None, limit: int = 100)`

- [ ] **Step 1: Write failing tests for event filters and summary**

Create `tests/test_api_read_models.py`:

```python
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
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
python -m pytest tests/test_api_read_models.py -v
```

Expected: FAIL because `integration_app.api.read_models` does not exist.

- [ ] **Step 3: Implement read models**

Create `src/integration_app/api/__init__.py`:

```python
"""Local read-only dashboard API."""
```

Create `src/integration_app/api/read_models.py`:

```python
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EventFilters:
    status: str | None = None
    connection_name: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    limit: int = 100


EVENT_COLUMNS = [
    "connection_name",
    "flow_type",
    "protocol",
    "local_path",
    "remote_path",
    "status",
    "detected_at",
    "sent_at",
    "confirmation_status",
    "confirmation_checked_at",
    "error_message",
]


def fetch_events(db_path: Path, filters: EventFilters) -> list[dict[str, object]]:
    sql = f"SELECT {', '.join(EVENT_COLUMNS)} FROM file_events"
    clauses: list[str] = []
    params: list[object] = []
    if filters.status:
        clauses.append("status = ?")
        params.append(filters.status)
    if filters.connection_name:
        clauses.append("connection_name = ?")
        params.append(filters.connection_name)
    if filters.date_from:
        clauses.append("date(detected_at) >= date(?)")
        params.append(filters.date_from)
    if filters.date_to:
        clauses.append("date(detected_at) <= date(?)")
        params.append(filters.date_to)
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY detected_at DESC LIMIT ?"
    params.append(max(1, min(filters.limit, 500)))
    with _connect(db_path) as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(row) for row in rows]


def fetch_summary(db_path: Path) -> dict[str, object]:
    rows = fetch_events(db_path, EventFilters(limit=500))
    summary: dict[str, object] = {
        "total_files": len(rows),
        "sent_count": 0,
        "confirmed_count": 0,
        "duplicate_count": 0,
        "failed_count": 0,
        "pending_count": 0,
        "unknown_count": 0,
        "last_detected_at": rows[0]["detected_at"] if rows else None,
    }
    known_statuses = {"sent", "confirmed", "duplicate", "failed"}
    for row in rows:
        status = str(row.get("status") or "")
        if status in {"sent", "confirmed"}:
            summary["sent_count"] = int(summary["sent_count"]) + 1
        if status == "confirmed":
            summary["confirmed_count"] = int(summary["confirmed_count"]) + 1
        elif status == "duplicate":
            summary["duplicate_count"] = int(summary["duplicate_count"]) + 1
        elif status == "failed":
            summary["failed_count"] = int(summary["failed_count"]) + 1
        elif status not in known_statuses:
            summary["unknown_count"] = int(summary["unknown_count"]) + 1
        if row.get("confirmation_status") == "pending":
            summary["pending_count"] = int(summary["pending_count"]) + 1
    return summary


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn
```

- [ ] **Step 4: Run tests and verify they pass**

Run:

```powershell
python -m pytest tests/test_api_read_models.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/integration_app/api tests/test_api_read_models.py
git commit -m "feat: add read-only api read models"
```

---

### Task 2: Add Report Listing And Supplier Aggregation

**Files:**
- Modify: `src/integration_app/api/read_models.py`
- Test: `tests/test_api_read_models.py`

**Interfaces:**
- Consumes: `fetch_events(db_path: Path, filters: EventFilters) -> list[dict[str, object]]`
- Produces: `list_reports(report_dir: Path) -> list[dict[str, object]]`
- Produces: `fetch_suppliers(db_path: Path) -> list[dict[str, object]]`

- [ ] **Step 1: Write failing tests for reports and suppliers**

Append to `tests/test_api_read_models.py`:

```python
from integration_app.api.read_models import fetch_suppliers, list_reports


def test_list_reports_classifies_report_files(tmp_path: Path):
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    (report_dir / "run-20260916-090101-summary.csv").write_text("x", encoding="utf-8")
    (report_dir / "generix-20260916-090101-exceptions.json").write_text("x", encoding="utf-8")
    (report_dir / "run-20260916-090101.csv").write_text("x", encoding="utf-8")

    rows = list_reports(report_dir)

    assert [row["name"] for row in rows] == [
        "run-20260916-090101-summary.csv",
        "generix-20260916-090101-exceptions.json",
        "run-20260916-090101.csv",
    ]
    assert rows[0]["kind"] == "summary"
    assert rows[1]["kind"] == "generix_exceptions"
    assert rows[2]["kind"] == "run"


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
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
python -m pytest tests/test_api_read_models.py -v
```

Expected: FAIL because functions are missing.

- [ ] **Step 3: Implement report listing and supplier aggregation**

Add to `src/integration_app/api/read_models.py`:

```python
from integration_app.reports.exporters import _enrich_row


def list_reports(report_dir: Path) -> list[dict[str, object]]:
    if not report_dir.exists():
        return []
    rows: list[dict[str, object]] = []
    for path in sorted(report_dir.iterdir(), key=lambda item: item.stat().st_mtime, reverse=True):
        if not path.is_file():
            continue
        rows.append(
            {
                "name": path.name,
                "path": str(path),
                "kind": _report_kind(path.name),
                "size_bytes": path.stat().st_size,
                "modified_at": path.stat().st_mtime,
            }
        )
    return rows


def fetch_suppliers(db_path: Path) -> list[dict[str, object]]:
    suppliers: dict[str, dict[str, object]] = {}
    for row in fetch_events(db_path, EventFilters(limit=500)):
        enriched = _enrich_row(row)
        supplier_name = str(enriched.get("edi_fornecedor_nome") or enriched.get("xml_seller_name") or "UNKNOWN")
        if supplier_name not in suppliers:
            suppliers[supplier_name] = {
                "supplier_name": supplier_name,
                "total_files": 0,
                "failed_count": 0,
                "duplicate_count": 0,
            }
        item = suppliers[supplier_name]
        item["total_files"] = int(item["total_files"]) + 1
        if row.get("status") == "failed":
            item["failed_count"] = int(item["failed_count"]) + 1
        if row.get("status") == "duplicate":
            item["duplicate_count"] = int(item["duplicate_count"]) + 1
    return [suppliers[name] for name in sorted(suppliers)]


def _report_kind(name: str) -> str:
    if "-summary." in name:
        return "summary"
    if "-exceptions." in name:
        return "generix_exceptions"
    if name.startswith("generix-"):
        return "generix"
    if name.startswith("run-"):
        return "run"
    return "other"
```

- [ ] **Step 4: Run tests and verify they pass**

Run:

```powershell
python -m pytest tests/test_api_read_models.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/integration_app/api/read_models.py tests/test_api_read_models.py
git commit -m "feat: expose report and supplier read models"
```

---

### Task 3: Add FastAPI App Endpoints

**Files:**
- Create: `src/integration_app/api/app.py`
- Test: `tests/test_api_app.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: read model functions from Tasks 1-2.
- Produces: `create_app(db_path: Path, report_dir: Path) -> FastAPI`

- [ ] **Step 1: Add dependencies**

Modify `pyproject.toml` dependencies:

```toml
dependencies = [
    "PyYAML>=6.0.2",
    "paramiko>=3.4.1",
    "openpyxl>=3.1.5",
    "fastapi>=0.115.0",
    "uvicorn>=0.30.0",
]
```

- [ ] **Step 2: Write failing endpoint tests**

Create `tests/test_api_app.py`:

```python
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
    assert events.json()["items"][0]["connection_name"] == "main"


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
```

- [ ] **Step 3: Run endpoint tests and verify they fail**

Run:

```powershell
python -m pytest tests/test_api_app.py -v
```

Expected: FAIL because `integration_app.api.app` does not exist or FastAPI dependency is missing.

- [ ] **Step 4: Implement app factory**

Create `src/integration_app/api/app.py`:

```python
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Query

from integration_app.api.read_models import EventFilters, fetch_events, fetch_summary, fetch_suppliers, list_reports


def create_app(db_path: Path, report_dir: Path) -> FastAPI:
    app = FastAPI(title="Relatorios Encomendas EDI EF API")

    @app.get("/health")
    def health() -> dict[str, object]:
        return {"status": "ok", "database_exists": db_path.exists()}

    @app.get("/summary")
    def summary() -> dict[str, object]:
        return fetch_summary(db_path)

    @app.get("/events")
    def events(
        status: str | None = None,
        connection_name: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = Query(100, ge=1, le=500),
    ) -> dict[str, object]:
        return {
            "items": fetch_events(
                db_path,
                EventFilters(
                    status=status,
                    connection_name=connection_name,
                    date_from=date_from,
                    date_to=date_to,
                    limit=limit,
                ),
            )
        }

    @app.get("/suppliers")
    def suppliers() -> dict[str, object]:
        return {"items": fetch_suppliers(db_path)}

    @app.get("/reports")
    def reports() -> dict[str, object]:
        return {"items": list_reports(report_dir)}

    return app
```

- [ ] **Step 5: Run endpoint tests and verify they pass**

Run:

```powershell
python -m pytest tests/test_api_app.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add pyproject.toml src/integration_app/api/app.py tests/test_api_app.py
git commit -m "feat: add local read-only api endpoints"
```

---

### Task 4: Add API CLI Entry Point And Documentation

**Files:**
- Create: `src/integration_app/api/__main__.py`
- Modify: `README.md`
- Test: `tests/test_api_cli.py`

**Interfaces:**
- Consumes: `create_app(db_path: Path, report_dir: Path) -> FastAPI`
- Produces: `main(argv: list[str] | None = None) -> int`

- [ ] **Step 1: Write failing CLI tests**

Create `tests/test_api_cli.py`:

```python
from pathlib import Path

from integration_app.api.__main__ import build_parser


def test_api_cli_defaults_to_local_paths():
    parser = build_parser()

    args = parser.parse_args([])

    assert args.db == Path("data/integration.db")
    assert args.reports == Path("reports")
    assert args.host == "127.0.0.1"
    assert args.port == 8000
```

- [ ] **Step 2: Run CLI test and verify it fails**

Run:

```powershell
python -m pytest tests/test_api_cli.py -v
```

Expected: FAIL because `integration_app.api.__main__` is missing.

- [ ] **Step 3: Implement CLI**

Create `src/integration_app/api/__main__.py`:

```python
from __future__ import annotations

import argparse
from pathlib import Path

import uvicorn

from integration_app.api.app import create_app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="integration-api")
    parser.add_argument("--db", type=Path, default=Path("data/integration.db"))
    parser.add_argument("--reports", type=Path, default=Path("reports"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    app = create_app(args.db, args.reports)
    uvicorn.run(app, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Document local API command**

Append to `README.md`:

````markdown
## API Local De Monitorização

Para consultar eventos, resumos e relatórios por HTTP local:

```powershell
python -m integration_app.api --db data/integration.db --reports reports
```

Endpoints principais:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/summary`
- `http://127.0.0.1:8000/events`
- `http://127.0.0.1:8000/suppliers`
- `http://127.0.0.1:8000/reports`

A API é apenas de leitura nesta fase.
````

- [ ] **Step 5: Run CLI test and full API tests**

Run:

```powershell
python -m pytest tests/test_api_cli.py tests/test_api_app.py tests/test_api_read_models.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add README.md src/integration_app/api/__main__.py tests/test_api_cli.py
git commit -m "feat: add local api runner"
```

---

## Final Verification

- [ ] Run full test suite:

```powershell
python -m pytest -v
```

Expected: PASS.

- [ ] Run a short import smoke test:

```powershell
python -c "from pathlib import Path; from integration_app.api.app import create_app; app=create_app(Path('data/integration.db'), Path('reports')); print(app.title)"
```

Expected output:

```text
Relatorios Encomendas EDI EF API
```

- [ ] Check git status:

```powershell
git status --short
```

Expected: no uncommitted implementation files.
