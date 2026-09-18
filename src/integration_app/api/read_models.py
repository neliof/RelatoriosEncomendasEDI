from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from integration_app.config import load_config
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


def fetch_connections(db_path: Path) -> list[dict[str, object]]:
    connections: dict[str, dict[str, object]] = {}
    for row in fetch_events(db_path, EventFilters(limit=500)):
        name = str(row.get("connection_name") or "")
        if name not in connections:
            connections[name] = {
                "connection_name": name,
                "protocol": row.get("protocol"),
                "total_files": 0,
                "sent_count": 0,
                "confirmed_count": 0,
                "duplicate_count": 0,
                "failed_count": 0,
                "pending_count": 0,
                "last_detected_at": row.get("detected_at"),
            }
        item = connections[name]
        status = str(row.get("status") or "")
        item["total_files"] = int(item["total_files"]) + 1
        if status in {"sent", "confirmed"}:
            item["sent_count"] = int(item["sent_count"]) + 1
        if status == "confirmed":
            item["confirmed_count"] = int(item["confirmed_count"]) + 1
        elif status == "duplicate":
            item["duplicate_count"] = int(item["duplicate_count"]) + 1
        elif status == "failed":
            item["failed_count"] = int(item["failed_count"]) + 1
        if row.get("confirmation_status") == "pending":
            item["pending_count"] = int(item["pending_count"]) + 1
    return [connections[name] for name in sorted(connections)]


def fetch_config_summary(config_path: Path) -> dict[str, object]:
    if not config_path.exists():
        return {"config_exists": False, "app": {}, "connections": []}
    config = load_config(config_path)
    return {
        "config_exists": True,
        "app": {
            "generix_storage_root": str(config.app.generix_storage_root) if config.app.generix_storage_root else None,
        },
        "connections": [
            {
                "name": connection.name,
                "enabled": connection.enabled,
                "flow_type": connection.flow_type,
                "protocol": connection.protocol,
                "host": connection.host,
                "port": connection.port,
                "username": connection.username,
                "source_dir": str(connection.source_dir),
                "remote_dir": connection.remote_dir,
                "file_pattern": connection.file_pattern,
                "sent_dir": connection.sent_dir,
                "error_dir": connection.error_dir,
                "duplicate_policy": connection.duplicate_policy,
                "confirm_remote_processing": connection.confirm_remote_processing,
                "has_password_env": connection.password_env is not None,
                "has_private_key": connection.private_key_path is not None,
                "schedule_enabled": connection.schedule_enabled,
                "schedule_frequency": connection.schedule_frequency,
                "schedule_interval": connection.schedule_interval,
                "schedule_hour": connection.schedule_hour,
                "schedule_minute": connection.schedule_minute,
            }
            for connection in config.connections
        ],
    }


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
        flow_type = str(row.get("flow_type") or "")
        if flow_type != "sent":
            continue
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


def fetch_clients(db_path: Path) -> list[dict[str, object]]:
    clients: dict[str, dict[str, object]] = {}
    for row in fetch_events(db_path, EventFilters(limit=500)):
        flow_type = str(row.get("flow_type") or "")
        if flow_type != "received":
            continue
        enriched = _enrich_row(row)
        client_name = str(enriched.get("edi_origin_name") or "UNKNOWN")
        if client_name not in clients:
            clients[client_name] = {
                "client_name": client_name,
                "total_files": 0,
                "failed_count": 0,
                "duplicate_count": 0,
            }
        item = clients[client_name]
        item["total_files"] = int(item["total_files"]) + 1
        if row.get("status") == "failed":
            item["failed_count"] = int(item["failed_count"]) + 1
        if row.get("status") == "duplicate":
            item["duplicate_count"] = int(item["duplicate_count"]) + 1
    return [clients[name] for name in sorted(clients)]


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def fetch_reports_summary(
    db_path: Path,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict[str, object]:
    sql = "SELECT COUNT(*) as total, status FROM file_events"
    params: list[object] = []

    where_clauses = []
    if date_from:
        where_clauses.append("date(detected_at) >= date(?)")
        params.append(date_from)
    if date_to:
        where_clauses.append("date(detected_at) <= date(?)")
        params.append(date_to)

    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)

    sql += " GROUP BY status"

    with _connect(db_path) as conn:
        rows = conn.execute(sql, params).fetchall()

    summary = {"total": 0, "sent": 0, "failed": 0, "confirmed": 0, "duplicate": 0}
    for row in rows:
        status = str(row["status"] or "")
        count = int(row["total"])
        summary["total"] += count
        if status in summary:
            summary[status] = count

    return summary


def fetch_reports_by_entity(
    db_path: Path,
    flow_type: str,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[dict[str, object]]:
    entity_field = "edi_origin_name" if flow_type == "received" else "edi_fornecedor_nome"
    entity_name_key = "origin_name" if flow_type == "received" else "supplier_name"

    sql = f"""
        SELECT
            {entity_field} as entity_name,
            COUNT(*) as total_files,
            SUM(CASE WHEN status = 'sent' OR status = 'confirmed' THEN 1 ELSE 0 END) as sent_count,
            SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_count,
            SUM(CASE WHEN status = 'duplicate' THEN 1 ELSE 0 END) as duplicate_count,
            MAX(detected_at) as last_activity
        FROM file_events
        WHERE flow_type = ?
    """
    params: list[object] = [flow_type]

    if date_from:
        sql += " AND date(detected_at) >= date(?)"
        params.append(date_from)
    if date_to:
        sql += " AND date(detected_at) <= date(?)"
        params.append(date_to)

    sql += " GROUP BY entity_name ORDER BY total_files DESC"

    with _connect(db_path) as conn:
        rows = conn.execute(sql, params).fetchall()

    return [
        {
            entity_name_key: str(row["entity_name"] or "UNKNOWN"),
            "total_files": int(row["total_files"]),
            "sent_count": int(row["sent_count"] or 0),
            "failed_count": int(row["failed_count"] or 0),
            "duplicate_count": int(row["duplicate_count"] or 0),
            "last_activity": str(row["last_activity"] or ""),
        }
        for row in rows
    ]


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
