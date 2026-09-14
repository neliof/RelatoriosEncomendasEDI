# Integracao FTP/SFTP e Generix MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python console application that runs one integration cycle, sends stable files by FTP/SFTP, records history in SQLite, checks remote confirmations, and exports reports.

**Architecture:** The application is a short-lived CLI process suitable for Windows Task Scheduler. It reads YAML configuration, uses focused service modules for file handling, transfer clients, storage and reporting, and keeps all operational state in SQLite.

**Tech Stack:** Python 3.11+, PyYAML, paramiko, openpyxl, pytest, sqlite3 from the standard library, ftplib from the standard library.

**Spec:** `docs/superpowers/specs/2026-09-14-integracao-ftp-sftp-generix-mvp-design.md`

## Global Constraints

- The command must support `run-once`.
- Configuration must be centralized in YAML.
- Multiple connections must be supported, each with active/inactive state.
- The MVP must run as a console/script process suitable for Windows Task Scheduler.
- File stability must be checked before upload.
- Successful files must move to `Enviados`; failed files must move to `Erros`.
- History must be stored in SQLite.
- Reports must be exported as CSV, Excel `.xlsx`, and JSON.
- Logs must be structured JSON Lines.
- FTP must use `ftplib`; SFTP must use `paramiko`.
- Failures in one connection must not stop the remaining connections.
- Remote confirmation is based on the uploaded file disappearing from the remote destination.
- Sensitive passwords should be referenced through environment variables.

---

## File Structure

- `pyproject.toml`: project metadata, dependencies, pytest configuration.
- `.gitignore`: Python, virtual environment, runtime database, logs and reports.
- `config.example.yaml`: documented example configuration.
- `src/integration_app/__init__.py`: package marker and version.
- `src/integration_app/app.py`: CLI entry point.
- `src/integration_app/config.py`: YAML loading and validation.
- `src/integration_app/models.py`: shared dataclasses and enum constants.
- `src/integration_app/logging_setup.py`: JSON Lines logging setup.
- `src/integration_app/core/files.py`: file discovery, stability and local moves.
- `src/integration_app/core/runner.py`: orchestration of one run cycle.
- `src/integration_app/storage/sqlite_store.py`: schema creation and persistence.
- `src/integration_app/transfers/base.py`: transfer client protocol and factory contract.
- `src/integration_app/transfers/ftp_client.py`: FTP implementation.
- `src/integration_app/transfers/sftp_client.py`: SFTP implementation.
- `src/integration_app/reports/exporters.py`: CSV, Excel and JSON reports.
- `src/integration_app/notifications/email.py`: disabled-by-default email notifier interface.
- `docs/generix-mailbox-mapping.md`: mapping template for the Generix mailbox.
- `docs/install-windows-task-scheduler.md`: installation and scheduling guide.
- `tests/`: focused pytest coverage per module.

---

### Task 1: Project Skeleton and Configuration Loader

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `config.example.yaml`
- Create: `src/integration_app/__init__.py`
- Create: `src/integration_app/config.py`
- Create: `src/integration_app/models.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `load_config(path: str | Path) -> AppConfig`
- Produces: `AppConfig`, `DefaultsConfig`, `ConnectionConfig`
- Produces: `ConnectionConfig.resolve_password() -> str | None`

- [ ] **Step 1: Write the failing configuration tests**

```python
from pathlib import Path

import pytest

from integration_app.config import load_config


def test_load_config_parses_enabled_connection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("LAB_X_SFTP_PASSWORD", "secret")
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
app:
  database_path: data/integration.db
  log_dir: logs
  report_dir: reports
defaults:
  stable_after_seconds: 30
  confirmation_timeout_minutes: 120
connections:
  - name: laboratorio_x
    enabled: true
    flow_type: generic
    protocol: sftp
    host: sftp.example.test
    port: 22
    username: user
    password_env: LAB_X_SFTP_PASSWORD
    source_dir: ./inbox
    remote_dir: /inbound
    file_pattern: "*.edi"
    sent_dir: Enviados
    error_dir: Erros
    confirm_remote_processing: true
""",
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.app.database_path == Path("data/integration.db")
    assert config.defaults.stable_after_seconds == 30
    assert config.connections[0].name == "laboratorio_x"
    assert config.connections[0].protocol == "sftp"
    assert config.connections[0].resolve_password() == "secret"


def test_load_config_rejects_duplicate_connection_names(tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
app:
  database_path: data/integration.db
  log_dir: logs
  report_dir: reports
defaults:
  stable_after_seconds: 30
  confirmation_timeout_minutes: 120
connections:
  - name: repeated
    enabled: true
    flow_type: generic
    protocol: ftp
    host: ftp.example.test
    port: 21
    username: user
    source_dir: ./a
    remote_dir: /inbound
    file_pattern: "*.txt"
  - name: repeated
    enabled: true
    flow_type: generic
    protocol: ftp
    host: ftp.example.test
    port: 21
    username: user
    source_dir: ./b
    remote_dir: /inbound
    file_pattern: "*.txt"
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Duplicate connection name: repeated"):
        load_config(config_path)
```

- [ ] **Step 2: Run tests and confirm they fail because the package does not exist**

Run: `python -m pytest tests/test_config.py -v`

Expected: `ModuleNotFoundError: No module named 'integration_app'`

- [ ] **Step 3: Add project metadata and dependencies**

Create `pyproject.toml`:

```toml
[project]
name = "relatorios-encomendas-edi-ef"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "PyYAML>=6.0.2",
    "paramiko>=3.4.1",
    "openpyxl>=3.1.5",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

- [ ] **Step 4: Add git ignore rules**

Create `.gitignore`:

```gitignore
.venv/
__pycache__/
*.pyc
.pytest_cache/
data/
logs/
reports/
*.db
*.sqlite
```

- [ ] **Step 5: Add the shared models**

Create `src/integration_app/models.py`:

```python
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppPaths:
    database_path: Path
    log_dir: Path
    report_dir: Path


@dataclass(frozen=True)
class DefaultsConfig:
    stable_after_seconds: int
    confirmation_timeout_minutes: int


@dataclass(frozen=True)
class ConnectionConfig:
    name: str
    enabled: bool
    flow_type: str
    protocol: str
    host: str
    port: int
    username: str
    source_dir: Path
    remote_dir: str
    file_pattern: str
    sent_dir: str = "Enviados"
    error_dir: str = "Erros"
    password_env: str | None = None
    private_key_path: Path | None = None
    private_key_passphrase_env: str | None = None
    confirm_remote_processing: bool = True

    def resolve_password(self) -> str | None:
        if self.password_env is None:
            return None
        return os.environ.get(self.password_env)


@dataclass(frozen=True)
class AppConfig:
    app: AppPaths
    defaults: DefaultsConfig
    connections: list[ConnectionConfig]
```

- [ ] **Step 6: Add the YAML loader and validation**

Create `src/integration_app/config.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from integration_app.models import AppConfig, AppPaths, ConnectionConfig, DefaultsConfig


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Configuration root must be a mapping")

    app_raw = _required_mapping(raw, "app")
    defaults_raw = _required_mapping(raw, "defaults")
    connections_raw = raw.get("connections")
    if not isinstance(connections_raw, list):
        raise ValueError("connections must be a list")

    connections = [_parse_connection(item) for item in connections_raw]
    _validate_unique_names(connections)

    return AppConfig(
        app=AppPaths(
            database_path=Path(_required_str(app_raw, "database_path")),
            log_dir=Path(_required_str(app_raw, "log_dir")),
            report_dir=Path(_required_str(app_raw, "report_dir")),
        ),
        defaults=DefaultsConfig(
            stable_after_seconds=_required_int(defaults_raw, "stable_after_seconds"),
            confirmation_timeout_minutes=_required_int(defaults_raw, "confirmation_timeout_minutes"),
        ),
        connections=connections,
    )


def _parse_connection(raw: Any) -> ConnectionConfig:
    if not isinstance(raw, dict):
        raise ValueError("Each connection must be a mapping")
    protocol = _required_str(raw, "protocol").lower()
    if protocol not in {"ftp", "sftp"}:
        raise ValueError(f"Unsupported protocol: {protocol}")
    return ConnectionConfig(
        name=_required_str(raw, "name"),
        enabled=bool(raw.get("enabled", True)),
        flow_type=str(raw.get("flow_type", "generic")),
        protocol=protocol,
        host=_required_str(raw, "host"),
        port=_required_int(raw, "port"),
        username=_required_str(raw, "username"),
        source_dir=Path(_required_str(raw, "source_dir")),
        remote_dir=_required_str(raw, "remote_dir"),
        file_pattern=str(raw.get("file_pattern", "*")),
        sent_dir=str(raw.get("sent_dir", "Enviados")),
        error_dir=str(raw.get("error_dir", "Erros")),
        password_env=raw.get("password_env"),
        private_key_path=Path(raw["private_key_path"]) if raw.get("private_key_path") else None,
        private_key_passphrase_env=raw.get("private_key_passphrase_env"),
        confirm_remote_processing=bool(raw.get("confirm_remote_processing", True)),
    )


def _validate_unique_names(connections: list[ConnectionConfig]) -> None:
    seen: set[str] = set()
    for connection in connections:
        if connection.name in seen:
            raise ValueError(f"Duplicate connection name: {connection.name}")
        seen.add(connection.name)


def _required_mapping(raw: dict[str, Any], key: str) -> dict[str, Any]:
    value = raw.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be a mapping")
    return value


def _required_str(raw: dict[str, Any], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _required_int(raw: dict[str, Any], key: str) -> int:
    value = raw.get(key)
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"{key} must be a non-negative integer")
    return value
```

- [ ] **Step 7: Add package marker and example config**

Create `src/integration_app/__init__.py`:

```python
__version__ = "0.1.0"
```

Create `config.example.yaml` using the example from the spec, with `confirm_remote_processing: true`.

- [ ] **Step 8: Run configuration tests**

Run: `python -m pytest tests/test_config.py -v`

Expected: 2 passed.

- [ ] **Step 9: Commit**

```bash
git add .gitignore pyproject.toml config.example.yaml src/integration_app tests/test_config.py
git commit -m "feat: add configuration loader"
```

---

### Task 2: SQLite Storage

**Files:**
- Create: `src/integration_app/storage/__init__.py`
- Create: `src/integration_app/storage/sqlite_store.py`
- Test: `tests/test_sqlite_store.py`

**Interfaces:**
- Consumes: `ConnectionConfig`
- Produces: `SQLiteStore(db_path: Path)`
- Produces: `SQLiteStore.initialize() -> None`
- Produces: `SQLiteStore.record_detected(connection: ConnectionConfig, local_path: Path, remote_path: str) -> int`
- Produces: `SQLiteStore.record_transfer_result(event_id: int, status: str, started_at: datetime, finished_at: datetime, error_message: str | None) -> None`
- Produces: `SQLiteStore.pending_confirmations() -> list[PendingConfirmation]`
- Produces: `SQLiteStore.record_confirmation(event_id: int, status: str, checked_at: datetime) -> None`
- Produces: `PendingConfirmation` dataclass

- [ ] **Step 1: Write failing storage tests**

```python
from datetime import UTC, datetime
from pathlib import Path

from integration_app.models import ConnectionConfig
from integration_app.storage.sqlite_store import SQLiteStore


def _connection(tmp_path: Path) -> ConnectionConfig:
    return ConnectionConfig(
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


def test_records_file_lifecycle(tmp_path: Path):
    store = SQLiteStore(tmp_path / "integration.db")
    store.initialize()
    connection = _connection(tmp_path)

    event_id = store.record_detected(connection, tmp_path / "a.txt", "/inbound/a.txt")
    started = datetime(2026, 9, 14, 10, 0, tzinfo=UTC)
    finished = datetime(2026, 9, 14, 10, 1, tzinfo=UTC)
    store.record_transfer_result(event_id, "sent", started, finished, None)
    pending = store.pending_confirmations()

    assert len(pending) == 1
    assert pending[0].event_id == event_id
    assert pending[0].remote_path == "/inbound/a.txt"

    store.record_confirmation(event_id, "confirmed", finished)
    assert store.pending_confirmations() == []
```

- [ ] **Step 2: Run the failing test**

Run: `python -m pytest tests/test_sqlite_store.py -v`

Expected: FAIL because `integration_app.storage.sqlite_store` is missing.

- [ ] **Step 3: Implement SQLite schema and repository**

Create `src/integration_app/storage/sqlite_store.py` with:

```python
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
```

- [ ] **Step 4: Add storage package marker**

Create `src/integration_app/storage/__init__.py`:

```python
```

- [ ] **Step 5: Run storage tests**

Run: `python -m pytest tests/test_sqlite_store.py -v`

Expected: 1 passed.

- [ ] **Step 6: Commit**

```bash
git add src/integration_app/storage tests/test_sqlite_store.py
git commit -m "feat: add sqlite storage"
```

---

### Task 3: File Discovery, Stability and Local Moves

**Files:**
- Create: `src/integration_app/core/__init__.py`
- Create: `src/integration_app/core/files.py`
- Test: `tests/test_files.py`

**Interfaces:**
- Consumes: `ConnectionConfig`
- Produces: `discover_files(connection: ConnectionConfig) -> list[Path]`
- Produces: `is_stable(path: Path, stable_after_seconds: int, now: datetime | None = None) -> bool`
- Produces: `move_to_status_dir(path: Path, status_dir_name: str) -> Path`
- Produces: `remote_path_for(connection: ConnectionConfig, local_path: Path) -> str`

- [ ] **Step 1: Write failing file tests**

```python
from datetime import UTC, datetime, timedelta
from pathlib import Path

from integration_app.core.files import discover_files, is_stable, move_to_status_dir, remote_path_for
from integration_app.models import ConnectionConfig


def _connection(tmp_path: Path) -> ConnectionConfig:
    return ConnectionConfig(
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


def test_discover_files_ignores_sent_and_error_dirs(tmp_path: Path):
    (tmp_path / "a.edi").write_text("ok", encoding="utf-8")
    (tmp_path / "Enviados").mkdir()
    (tmp_path / "Enviados" / "b.edi").write_text("old", encoding="utf-8")
    (tmp_path / "Erros").mkdir()
    (tmp_path / "Erros" / "c.edi").write_text("bad", encoding="utf-8")

    assert discover_files(_connection(tmp_path)) == [tmp_path / "a.edi"]


def test_is_stable_uses_modified_time(tmp_path: Path):
    file_path = tmp_path / "a.edi"
    file_path.write_text("ok", encoding="utf-8")
    now = datetime(2026, 9, 14, 12, 0, tzinfo=UTC)
    old_timestamp = (now - timedelta(seconds=45)).timestamp()
    file_path.touch()
    import os
    os.utime(file_path, (old_timestamp, old_timestamp))

    assert is_stable(file_path, stable_after_seconds=30, now=now) is True


def test_move_to_status_dir_adds_timestamp_on_conflict(tmp_path: Path):
    file_path = tmp_path / "a.edi"
    file_path.write_text("new", encoding="utf-8")
    sent_dir = tmp_path / "Enviados"
    sent_dir.mkdir()
    (sent_dir / "a.edi").write_text("old", encoding="utf-8")

    moved = move_to_status_dir(file_path, "Enviados")

    assert moved.parent == sent_dir
    assert moved.name.startswith("a_")
    assert moved.suffix == ".edi"


def test_remote_path_for_joins_with_forward_slashes(tmp_path: Path):
    assert remote_path_for(_connection(tmp_path), tmp_path / "a.edi") == "/inbound/a.edi"
```

- [ ] **Step 2: Run the failing tests**

Run: `python -m pytest tests/test_files.py -v`

Expected: FAIL because `integration_app.core.files` is missing.

- [ ] **Step 3: Implement file utilities**

Create `src/integration_app/core/files.py`:

```python
from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from integration_app.models import ConnectionConfig


def discover_files(connection: ConnectionConfig) -> list[Path]:
    source_dir = connection.source_dir
    if not source_dir.exists():
        return []
    excluded = {connection.sent_dir.lower(), connection.error_dir.lower()}
    files = [
        path
        for path in source_dir.glob(connection.file_pattern)
        if path.is_file() and not any(part.lower() in excluded for part in path.relative_to(source_dir).parts[:-1])
    ]
    return sorted(files)


def is_stable(path: Path, stable_after_seconds: int, now: datetime | None = None) -> bool:
    current_time = now or datetime.now(UTC)
    modified = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
    return (current_time - modified).total_seconds() >= stable_after_seconds


def move_to_status_dir(path: Path, status_dir_name: str) -> Path:
    target_dir = path.parent / status_dir_name
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / path.name
    if target.exists():
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        target = target_dir / f"{path.stem}_{timestamp}{path.suffix}"
    return shutil.move(str(path), str(target)) and target


def remote_path_for(connection: ConnectionConfig, local_path: Path) -> str:
    return str(PurePosixPath(connection.remote_dir) / local_path.name)
```

- [ ] **Step 4: Add core package marker**

Create `src/integration_app/core/__init__.py`:

```python
```

- [ ] **Step 5: Run file tests**

Run: `python -m pytest tests/test_files.py -v`

Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add src/integration_app/core tests/test_files.py
git commit -m "feat: add file processing utilities"
```

---

### Task 4: Transfer Client Interfaces and Implementations

**Files:**
- Create: `src/integration_app/transfers/__init__.py`
- Create: `src/integration_app/transfers/base.py`
- Create: `src/integration_app/transfers/ftp_client.py`
- Create: `src/integration_app/transfers/sftp_client.py`
- Test: `tests/test_transfer_factory.py`

**Interfaces:**
- Consumes: `ConnectionConfig`
- Produces: `TransferClient` protocol with `connect()`, `upload(local_path: Path, remote_path: str)`, `exists(remote_path: str) -> bool`, `close()`
- Produces: `build_transfer_client(connection: ConnectionConfig) -> TransferClient`
- Produces: `FTPTransferClient`
- Produces: `SFTPTransferClient`

- [ ] **Step 1: Write failing factory tests**

```python
from pathlib import Path

import pytest

from integration_app.models import ConnectionConfig
from integration_app.transfers.base import build_transfer_client
from integration_app.transfers.ftp_client import FTPTransferClient
from integration_app.transfers.sftp_client import SFTPTransferClient


def _connection(protocol: str) -> ConnectionConfig:
    return ConnectionConfig(
        name="lab",
        enabled=True,
        flow_type="generic",
        protocol=protocol,
        host="example.test",
        port=22 if protocol == "sftp" else 21,
        username="user",
        source_dir=Path("."),
        remote_dir="/inbound",
        file_pattern="*.edi",
    )


def test_build_transfer_client_returns_ftp_client():
    assert isinstance(build_transfer_client(_connection("ftp")), FTPTransferClient)


def test_build_transfer_client_returns_sftp_client():
    assert isinstance(build_transfer_client(_connection("sftp")), SFTPTransferClient)


def test_build_transfer_client_rejects_unknown_protocol():
    with pytest.raises(ValueError, match="Unsupported protocol: smtp"):
        build_transfer_client(_connection("smtp"))
```

- [ ] **Step 2: Run the failing tests**

Run: `python -m pytest tests/test_transfer_factory.py -v`

Expected: FAIL because transfer modules are missing.

- [ ] **Step 3: Implement transfer protocol and factory**

Create `src/integration_app/transfers/base.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Protocol

from integration_app.models import ConnectionConfig


class TransferClient(Protocol):
    def connect(self) -> None:
        ...

    def upload(self, local_path: Path, remote_path: str) -> None:
        ...

    def exists(self, remote_path: str) -> bool:
        ...

    def close(self) -> None:
        ...


def build_transfer_client(connection: ConnectionConfig) -> TransferClient:
    if connection.protocol == "ftp":
        from integration_app.transfers.ftp_client import FTPTransferClient

        return FTPTransferClient(connection)
    if connection.protocol == "sftp":
        from integration_app.transfers.sftp_client import SFTPTransferClient

        return SFTPTransferClient(connection)
    raise ValueError(f"Unsupported protocol: {connection.protocol}")
```

- [ ] **Step 4: Implement FTP client**

Create `src/integration_app/transfers/ftp_client.py`:

```python
from __future__ import annotations

from ftplib import FTP
from pathlib import Path, PurePosixPath

from integration_app.models import ConnectionConfig


class FTPTransferClient:
    def __init__(self, connection: ConnectionConfig):
        self.connection = connection
        self.client: FTP | None = None

    def connect(self) -> None:
        client = FTP()
        client.connect(self.connection.host, self.connection.port, timeout=30)
        client.login(self.connection.username, self.connection.resolve_password() or "")
        self.client = client

    def upload(self, local_path: Path, remote_path: str) -> None:
        if self.client is None:
            raise RuntimeError("FTP client is not connected")
        remote = PurePosixPath(remote_path)
        self.client.cwd(str(remote.parent))
        with local_path.open("rb") as handle:
            self.client.storbinary(f"STOR {remote.name}", handle)

    def exists(self, remote_path: str) -> bool:
        if self.client is None:
            raise RuntimeError("FTP client is not connected")
        remote = PurePosixPath(remote_path)
        current = self.client.pwd()
        try:
            self.client.cwd(str(remote.parent))
            return remote.name in self.client.nlst()
        finally:
            self.client.cwd(current)

    def close(self) -> None:
        if self.client is not None:
            self.client.quit()
            self.client = None
```

- [ ] **Step 5: Implement SFTP client**

Create `src/integration_app/transfers/sftp_client.py`:

```python
from __future__ import annotations

from pathlib import Path

import paramiko

from integration_app.models import ConnectionConfig


class SFTPTransferClient:
    def __init__(self, connection: ConnectionConfig):
        self.connection = connection
        self.transport: paramiko.Transport | None = None
        self.client: paramiko.SFTPClient | None = None

    def connect(self) -> None:
        transport = paramiko.Transport((self.connection.host, self.connection.port))
        password = self.connection.resolve_password()
        if self.connection.private_key_path is not None:
            passphrase = None
            if self.connection.private_key_passphrase_env:
                import os
                passphrase = os.environ.get(self.connection.private_key_passphrase_env)
            key = paramiko.RSAKey.from_private_key_file(str(self.connection.private_key_path), password=passphrase)
            transport.connect(username=self.connection.username, pkey=key)
        else:
            transport.connect(username=self.connection.username, password=password)
        self.transport = transport
        self.client = paramiko.SFTPClient.from_transport(transport)

    def upload(self, local_path: Path, remote_path: str) -> None:
        if self.client is None:
            raise RuntimeError("SFTP client is not connected")
        self.client.put(str(local_path), remote_path)

    def exists(self, remote_path: str) -> bool:
        if self.client is None:
            raise RuntimeError("SFTP client is not connected")
        try:
            self.client.stat(remote_path)
            return True
        except FileNotFoundError:
            return False

    def close(self) -> None:
        if self.client is not None:
            self.client.close()
            self.client = None
        if self.transport is not None:
            self.transport.close()
            self.transport = None
```

- [ ] **Step 6: Add transfer package marker**

Create `src/integration_app/transfers/__init__.py`:

```python
```

- [ ] **Step 7: Run transfer tests**

Run: `python -m pytest tests/test_transfer_factory.py -v`

Expected: 3 passed.

- [ ] **Step 8: Commit**

```bash
git add src/integration_app/transfers tests/test_transfer_factory.py
git commit -m "feat: add transfer clients"
```

---

### Task 5: Run Cycle Orchestration

**Files:**
- Create: `src/integration_app/core/runner.py`
- Test: `tests/test_runner.py`

**Interfaces:**
- Consumes: `AppConfig`, `SQLiteStore`, `build_transfer_client`, file utilities
- Produces: `RunSummary(processed: int, sent: int, failed: int, skipped_unstable: int, confirmed: int, confirmation_timeouts: int)`
- Produces: `run_once(config: AppConfig, store: SQLiteStore, client_factory: Callable[[ConnectionConfig], TransferClient] = build_transfer_client) -> RunSummary`

- [ ] **Step 1: Write failing orchestration tests**

```python
from pathlib import Path

from integration_app.core.runner import run_once
from integration_app.models import AppConfig, AppPaths, ConnectionConfig, DefaultsConfig
from integration_app.storage.sqlite_store import SQLiteStore


class FakeClient:
    def __init__(self):
        self.uploaded = []
        self.remote_exists = False

    def connect(self):
        return None

    def upload(self, local_path: Path, remote_path: str):
        self.uploaded.append((local_path, remote_path))

    def exists(self, remote_path: str) -> bool:
        return self.remote_exists

    def close(self):
        return None


def test_run_once_uploads_stable_file_and_moves_to_sent(tmp_path: Path):
    source = tmp_path / "inbox"
    source.mkdir()
    file_path = source / "order.edi"
    file_path.write_text("EDI", encoding="utf-8")

    config = AppConfig(
        app=AppPaths(tmp_path / "data" / "integration.db", tmp_path / "logs", tmp_path / "reports"),
        defaults=DefaultsConfig(stable_after_seconds=0, confirmation_timeout_minutes=120),
        connections=[
            ConnectionConfig(
                name="lab",
                enabled=True,
                flow_type="generic",
                protocol="ftp",
                host="ftp.example.test",
                port=21,
                username="user",
                source_dir=source,
                remote_dir="/inbound",
                file_pattern="*.edi",
            )
        ],
    )
    store = SQLiteStore(config.app.database_path)
    store.initialize()
    fake = FakeClient()

    summary = run_once(config, store, client_factory=lambda connection: fake)

    assert summary.sent == 1
    assert fake.uploaded == [(file_path, "/inbound/order.edi")]
    assert (source / "Enviados" / "order.edi").exists()
```

- [ ] **Step 2: Run the failing test**

Run: `python -m pytest tests/test_runner.py -v`

Expected: FAIL because `integration_app.core.runner` is missing.

- [ ] **Step 3: Implement `run_once`**

Create `src/integration_app/core/runner.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Callable

from integration_app.core.files import discover_files, is_stable, move_to_status_dir, remote_path_for
from integration_app.models import AppConfig, ConnectionConfig
from integration_app.storage.sqlite_store import SQLiteStore
from integration_app.transfers.base import TransferClient, build_transfer_client


@dataclass(frozen=True)
class RunSummary:
    processed: int = 0
    sent: int = 0
    failed: int = 0
    skipped_unstable: int = 0
    confirmed: int = 0
    confirmation_timeouts: int = 0

    def add(self, **changes: int) -> "RunSummary":
        values = self.__dict__.copy()
        for key, value in changes.items():
            values[key] += value
        return RunSummary(**values)


def run_once(
    config: AppConfig,
    store: SQLiteStore,
    client_factory: Callable[[ConnectionConfig], TransferClient] = build_transfer_client,
) -> RunSummary:
    summary = RunSummary()
    enabled = [connection for connection in config.connections if connection.enabled]
    for connection in enabled:
        summary = _check_pending_confirmations(config, store, connection, client_factory, summary)
        for local_path in discover_files(connection):
            if not is_stable(local_path, config.defaults.stable_after_seconds):
                summary = summary.add(skipped_unstable=1)
                continue
            remote_path = remote_path_for(connection, local_path)
            event_id = store.record_detected(connection, local_path, remote_path)
            started = datetime.now(UTC)
            client = client_factory(connection)
            try:
                client.connect()
                client.upload(local_path, remote_path)
                finished = datetime.now(UTC)
                store.record_transfer_result(event_id, "sent", started, finished, None)
                move_to_status_dir(local_path, connection.sent_dir)
                summary = summary.add(processed=1, sent=1)
            except Exception as exc:
                finished = datetime.now(UTC)
                store.record_transfer_result(event_id, "failed", started, finished, str(exc))
                if local_path.exists():
                    move_to_status_dir(local_path, connection.error_dir)
                summary = summary.add(processed=1, failed=1)
            finally:
                client.close()
    return summary


def _check_pending_confirmations(
    config: AppConfig,
    store: SQLiteStore,
    connection: ConnectionConfig,
    client_factory: Callable[[ConnectionConfig], TransferClient],
    summary: RunSummary,
) -> RunSummary:
    pending = [item for item in store.pending_confirmations() if item.connection_name == connection.name]
    if not pending:
        return summary
    client = client_factory(connection)
    try:
        client.connect()
        for item in pending:
            checked_at = datetime.now(UTC)
            if not client.exists(item.remote_path):
                store.record_confirmation(item.event_id, "confirmed", checked_at)
                summary = summary.add(confirmed=1)
            elif checked_at - item.sent_at > timedelta(minutes=config.defaults.confirmation_timeout_minutes):
                store.record_confirmation(item.event_id, "confirmation_timeout", checked_at)
                summary = summary.add(confirmation_timeouts=1)
    finally:
        client.close()
    return summary
```

- [ ] **Step 4: Run orchestration test**

Run: `python -m pytest tests/test_runner.py -v`

Expected: 1 passed.

- [ ] **Step 5: Run all tests**

Run: `python -m pytest -v`

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/integration_app/core/runner.py tests/test_runner.py
git commit -m "feat: orchestrate run cycle"
```

---

### Task 6: Report Exporters

**Files:**
- Create: `src/integration_app/reports/__init__.py`
- Create: `src/integration_app/reports/exporters.py`
- Modify: `src/integration_app/storage/sqlite_store.py`
- Test: `tests/test_reports.py`

**Interfaces:**
- Consumes: `SQLiteStore`
- Produces: `SQLiteStore.report_rows() -> list[dict[str, object]]`
- Produces: `export_reports(store: SQLiteStore, report_dir: Path, run_id: str) -> list[Path]`

- [ ] **Step 1: Write failing report test**

```python
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
```

- [ ] **Step 2: Run the failing test**

Run: `python -m pytest tests/test_reports.py -v`

Expected: FAIL because `integration_app.reports.exporters` is missing.

- [ ] **Step 3: Add report query to storage**

Add this method to `SQLiteStore`:

```python
    def report_rows(self) -> list[dict[str, object]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT connection_name, flow_type, protocol, local_path, remote_path,
                       status, detected_at, sent_at, confirmation_status,
                       confirmation_checked_at, error_message
                FROM file_events
                ORDER BY detected_at ASC
                """
            ).fetchall()
        return [dict(row) for row in rows]
```

- [ ] **Step 4: Implement report exporters**

Create `src/integration_app/reports/exporters.py`:

```python
from __future__ import annotations

import csv
import json
from pathlib import Path

from openpyxl import Workbook

from integration_app.storage.sqlite_store import SQLiteStore


REPORT_COLUMNS = [
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


def export_reports(store: SQLiteStore, report_dir: Path, run_id: str) -> list[Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    rows = store.report_rows()
    csv_path = report_dir / f"{run_id}.csv"
    json_path = report_dir / f"{run_id}.json"
    xlsx_path = report_dir / f"{run_id}.xlsx"
    _write_csv(csv_path, rows)
    _write_json(json_path, rows)
    _write_xlsx(xlsx_path, rows)
    return [csv_path, json_path, xlsx_path]


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REPORT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")


def _write_xlsx(path: Path, rows: list[dict[str, object]]) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Report"
    sheet.append(REPORT_COLUMNS)
    for row in rows:
        sheet.append([row.get(column) for column in REPORT_COLUMNS])
    workbook.save(path)
```

- [ ] **Step 5: Add reports package marker**

Create `src/integration_app/reports/__init__.py`:

```python
```

- [ ] **Step 6: Run report tests**

Run: `python -m pytest tests/test_reports.py -v`

Expected: 1 passed.

- [ ] **Step 7: Commit**

```bash
git add src/integration_app/storage/sqlite_store.py src/integration_app/reports tests/test_reports.py
git commit -m "feat: export integration reports"
```

---

### Task 7: CLI, Logging and Documentation

**Files:**
- Create: `src/integration_app/logging_setup.py`
- Create: `src/integration_app/app.py`
- Create: `src/integration_app/notifications/__init__.py`
- Create: `src/integration_app/notifications/email.py`
- Create: `docs/generix-mailbox-mapping.md`
- Create: `docs/install-windows-task-scheduler.md`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `load_config`, `SQLiteStore`, `run_once`, `export_reports`
- Produces: `main(argv: list[str] | None = None) -> int`
- Produces: `configure_json_logging(log_dir: Path) -> Path`
- Produces: `EmailNotifier(enabled: bool = False).send(subject: str, body: str) -> None`

- [ ] **Step 1: Write failing CLI test**

```python
from pathlib import Path

from integration_app.app import main


def test_main_run_once_returns_zero(tmp_path: Path):
    source = tmp_path / "inbox"
    source.mkdir()
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        f"""
app:
  database_path: "{tmp_path / 'data' / 'integration.db'}"
  log_dir: "{tmp_path / 'logs'}"
  report_dir: "{tmp_path / 'reports'}"
defaults:
  stable_after_seconds: 0
  confirmation_timeout_minutes: 120
connections: []
""",
        encoding="utf-8",
    )

    exit_code = main(["run-once", "--config", str(config_path)])

    assert exit_code == 0
    assert (tmp_path / "data" / "integration.db").exists()
    assert any((tmp_path / "reports").glob("*.csv"))
```

- [ ] **Step 2: Run the failing CLI test**

Run: `python -m pytest tests/test_cli.py -v`

Expected: FAIL because `integration_app.app` is missing.

- [ ] **Step 3: Implement JSON Lines logging**

Create `src/integration_app/logging_setup.py`:

```python
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path


class JsonLineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_json_logging(log_dir: Path) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"integration-{datetime.now(UTC).strftime('%Y%m%d')}.jsonl"
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(JsonLineFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    return log_path
```

- [ ] **Step 4: Implement disabled email notifier**

Create `src/integration_app/notifications/email.py`:

```python
from __future__ import annotations


class EmailNotifier:
    def __init__(self, enabled: bool = False):
        self.enabled = enabled

    def send(self, subject: str, body: str) -> None:
        if not self.enabled:
            return None
        raise RuntimeError("Email notifications are not configured in the MVP")
```

Create `src/integration_app/notifications/__init__.py`:

```python
```

- [ ] **Step 5: Implement CLI**

Create `src/integration_app/app.py`:

```python
from __future__ import annotations

import argparse
import logging
from datetime import UTC, datetime
from pathlib import Path

from integration_app.config import load_config
from integration_app.core.runner import run_once
from integration_app.logging_setup import configure_json_logging
from integration_app.reports.exporters import export_reports
from integration_app.storage.sqlite_store import SQLiteStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="integration-app")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run-once")
    run_parser.add_argument("--config", required=True)
    args = parser.parse_args(argv)

    if args.command == "run-once":
        return _run_once_command(Path(args.config))
    return 2


def _run_once_command(config_path: Path) -> int:
    config = load_config(config_path)
    configure_json_logging(config.app.log_dir)
    logging.info("Starting integration run")
    store = SQLiteStore(config.app.database_path)
    store.initialize()
    summary = run_once(config, store)
    run_id = datetime.now(UTC).strftime("run-%Y%m%d-%H%M%S")
    export_reports(store, config.app.report_dir, run_id)
    logging.info("Finished integration run: %s", summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: Add Generix mapping document**

Create `docs/generix-mailbox-mapping.md` with these sections:

```markdown
# Mapeamento Mailbox Generix

## Objetivo

Registar a estrutura real de pastas e indicadores da mailbox Generix antes de activar regras especificas de EDI.

## Farmacias para ARTSOFT

| Elemento | Valor observado |
| --- | --- |
| Pasta onde a mailbox deixa ficheiros recebidos | |
| Padrao de ficheiro | |
| Pasta de ficheiros importados pelo ARTSOFT | |
| Pasta de erros | |
| Indicador de sucesso | |
| Indicador de erro | |

## ARTSOFT para Laboratorios

| Elemento | Valor observado |
| --- | --- |
| Pasta onde o ARTSOFT gera encomendas | |
| Padrao de ficheiro | |
| Pasta recolhida pela mailbox | |
| Pasta de enviados/confirmados | |
| Pasta de erros | |
| Indicador de envio ao laboratorio | |

## Regras por Entidade

| Entidade | Tipo | Padrao | Pasta | Observacoes |
| --- | --- | --- | --- | --- |
```

- [ ] **Step 7: Add Windows installation document**

Create `docs/install-windows-task-scheduler.md` with:

```markdown
# Instalacao no Windows Task Scheduler

## Preparacao

1. Instalar Python 3.11 ou superior.
2. Criar ambiente virtual: `python -m venv .venv`.
3. Activar ambiente: `.venv\Scripts\Activate.ps1`.
4. Instalar dependencias: `python -m pip install -e .[dev]`.
5. Copiar `config.example.yaml` para `config.yaml`.
6. Definir variaveis de ambiente das passwords usadas no YAML.

## Execucao Manual

```powershell
python -m integration_app.app run-once --config config.yaml
```

## Agendamento

No Task Scheduler, criar uma tarefa com:

- Program/script: caminho para `.venv\Scripts\python.exe`.
- Arguments: `-m integration_app.app run-once --config C:\caminho\config.yaml`.
- Start in: pasta raiz do projecto.
- Trigger: intervalo operacional escolhido, por exemplo 5 minutos.

## Verificacao

Confirmar que existem ficheiros em:

- `logs`
- `reports`
- `data/integration.db`
```

- [ ] **Step 8: Run CLI tests and all tests**

Run: `python -m pytest tests/test_cli.py -v`

Expected: 1 passed.

Run: `python -m pytest -v`

Expected: all tests pass.

- [ ] **Step 9: Commit**

```bash
git add src/integration_app/logging_setup.py src/integration_app/app.py src/integration_app/notifications docs/generix-mailbox-mapping.md docs/install-windows-task-scheduler.md tests/test_cli.py
git commit -m "feat: add cli and operational docs"
```

---

### Task 8: End-to-End Dry Run and README

**Files:**
- Create: `README.md`
- Test: manual verification in a temporary local folder

**Interfaces:**
- Consumes: complete CLI application
- Produces: documented project entry point and manual acceptance evidence

- [ ] **Step 1: Create README**

Create `README.md`:

```markdown
# Relatorios Encomendas EDI EF

Aplicacao Python para integrar ficheiros por FTP/SFTP e preparar os fluxos EDI Generix de farmacias, ARTSOFT e laboratorios.

## Execucao Rapida

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .[dev]
copy config.example.yaml config.yaml
python -m integration_app.app run-once --config config.yaml
```

## Componentes

- Configuracao em YAML.
- Execucao `run-once` para Windows Task Scheduler.
- Historico SQLite.
- Relatorios CSV, Excel e JSON.
- Logs JSON Lines.
- Clientes FTP e SFTP.

## Documentacao

- Design: `docs/superpowers/specs/2026-09-14-integracao-ftp-sftp-generix-mvp-design.md`
- Plano: `docs/superpowers/plans/2026-09-14-integracao-ftp-sftp-generix-mvp-implementation.md`
- Generix: `docs/generix-mailbox-mapping.md`
- Windows Task Scheduler: `docs/install-windows-task-scheduler.md`
```

- [ ] **Step 2: Run automated tests**

Run: `python -m pytest -v`

Expected: all tests pass.

- [ ] **Step 3: Run an empty configuration smoke test**

Create a temporary config with no connections and run:

```powershell
python -m integration_app.app run-once --config .\config.example.yaml
```

Expected when `config.example.yaml` contains unreachable example hosts: do not use the example for live transfer. Instead, copy it to a temporary config with `connections: []` and verify exit code `0`, generated reports, generated logs and SQLite database.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: add project readme"
```

---

## Self-Review

- Spec coverage: configuration, multiple connections, console `run-once`, FTP/SFTP clients, stability checks, local sent/error moves, SQLite history, confirmation checks, reports, logs and Windows scheduling documentation are covered by Tasks 1-8.
- Deferred from MVP implementation: native Windows service, SQL Server, GUI, external secret vault and direct ARTSOFT/Generix APIs remain outside the approved MVP scope.
- Placeholder scan: this plan contains no unfinished markers or unspecified implementation steps.
- Type consistency: `ConnectionConfig`, `AppConfig`, `SQLiteStore`, `TransferClient`, `run_once` and `export_reports` signatures are introduced before use in later tasks.
