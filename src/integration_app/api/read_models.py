from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from integration_app.reports.exporters import _enrich_row


@dataclass(frozen=True)
class EventFilters:
    status: str | None = None
    connection_name: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    limit: int = 100


EVENT_COLUMNS = [
    "id",
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
    return [_enrich_row(dict(row)) for row in rows]


def fetch_event_detail(db_path: Path, event_id: int) -> dict[str, object] | None:
    sql = f"SELECT {', '.join(EVENT_COLUMNS)} FROM file_events WHERE id = ?"
    with _connect(db_path) as conn:
        row = conn.execute(sql, (event_id,)).fetchone()
    if row is None:
        return None
    return _enrich_row(dict(row))


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


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


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
