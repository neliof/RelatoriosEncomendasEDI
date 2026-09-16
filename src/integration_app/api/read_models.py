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
