from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from integration_app.models import ConnectionConfig


@dataclass(frozen=True)
class PendingConfirmation:
    event_id: int
    connection_name: str
    protocol: str
    host: str
    port: int
    username: str
    remote_path: str
    sent_at: datetime


class SQLiteStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS file_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    connection_name TEXT NOT NULL,
                    flow_type TEXT NOT NULL,
                    protocol TEXT NOT NULL,
                    host TEXT NOT NULL,
                    port INTEGER NOT NULL,
                    username TEXT NOT NULL,
                    local_path TEXT NOT NULL,
                    remote_path TEXT NOT NULL,
                    status TEXT NOT NULL,
                    detected_at TEXT NOT NULL,
                    sent_at TEXT,
                    confirmation_status TEXT,
                    confirmation_checked_at TEXT,
                    error_message TEXT
                );
                CREATE TABLE IF NOT EXISTS transfer_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT NOT NULL,
                    error_message TEXT,
                    FOREIGN KEY(event_id) REFERENCES file_events(id)
                );
                """
            )

    def record_detected(self, connection: ConnectionConfig, local_path: Path, remote_path: str) -> int:
        now = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO file_events (
                    connection_name, flow_type, protocol, host, port, username,
                    local_path, remote_path, status, detected_at, confirmation_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    connection.name,
                    connection.flow_type,
                    connection.protocol,
                    connection.host,
                    connection.port,
                    connection.username,
                    str(local_path),
                    remote_path,
                    "detected",
                    now,
                    "pending" if connection.confirm_remote_processing else "disabled",
                ),
            )
            return int(cursor.lastrowid)

    def record_transfer_result(
        self,
        event_id: int,
        status: str,
        started_at: datetime,
        finished_at: datetime,
        error_message: str | None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO transfer_attempts (event_id, status, started_at, finished_at, error_message) VALUES (?, ?, ?, ?, ?)",
                (event_id, status, started_at.isoformat(), finished_at.isoformat(), error_message),
            )
            conn.execute(
                "UPDATE file_events SET status = ?, sent_at = ?, error_message = ? WHERE id = ?",
                (status, finished_at.isoformat() if status == "sent" else None, error_message, event_id),
            )

    def pending_confirmations(self) -> list[PendingConfirmation]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, connection_name, protocol, host, port, username, remote_path, sent_at
                FROM file_events
                WHERE status = 'sent' AND confirmation_status = 'pending'
                ORDER BY sent_at ASC
                """
            ).fetchall()
        return [
            PendingConfirmation(
                event_id=row["id"],
                connection_name=row["connection_name"],
                protocol=row["protocol"],
                host=row["host"],
                port=row["port"],
                username=row["username"],
                remote_path=row["remote_path"],
                sent_at=datetime.fromisoformat(row["sent_at"]),
            )
            for row in rows
        ]

    def record_confirmation(self, event_id: int, status: str, checked_at: datetime) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE file_events SET status = ?, confirmation_status = ?, confirmation_checked_at = ? WHERE id = ?",
                (status, status, checked_at.isoformat(), event_id),
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
