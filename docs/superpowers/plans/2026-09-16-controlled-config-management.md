# Controlled Config Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add controlled local configuration updates for existing connections, with backups, validation and sensitive-field blocking.

**Architecture:** Add `integration_app.api.config_management` for YAML update mechanics and keep HTTP handling in `api.app`. The dashboard only toggles existing connection state in this phase; all writes go through backup, validation with `load_config`, and atomic replacement.

**Tech Stack:** Python 3.11+, FastAPI, PyYAML, pathlib, pytest, FastAPI TestClient, plain JavaScript.

**Spec:** `docs/superpowers/specs/2026-09-16-controlled-config-management-design.md`

## Global Constraints

- API remains local.
- Do not show or return `password_env`, `private_key_path`, or `private_key_passphrase_env`.
- Do not allow updates to `password_env`, `private_key_path`, `private_key_passphrase_env`, `username`, `host`, `port`, or `protocol`.
- Only update existing connections.
- Do not create or delete connections.
- Create a backup before replacing `config.yaml`.
- Validate the updated YAML with `load_config` before replacing the original.
- If validation fails, leave the original `config.yaml` intact.
- Use TDD for implementation changes.

---

## File Structure

- Create `src/integration_app/api/config_management.py`: safe YAML mutation, backup, validation and atomic replace.
- Modify `src/integration_app/api/app.py`: add `PATCH /config/connections/{name}`.
- Modify `src/integration_app/api/static/dashboard.js`: add activate/deactivate action in configuration list.
- Modify `src/integration_app/api/static/dashboard.css`: action button/status styling if needed.
- Modify `tests/test_api_app.py`: API endpoint and dashboard contract tests.
- Create `tests/test_config_management.py`: pure config-management tests.
- Modify `README.md`: document controlled config update behaviour.

---

### Task 1: Add Safe Config Update Module

**Files:**
- Create: `src/integration_app/api/config_management.py`
- Test: `tests/test_config_management.py`

**Interfaces:**
- Produces: `ConfigUpdateError(message: str, status_code: int = 400)`
- Produces: `update_connection_config(config_path: Path, connection_name: str, updates: dict[str, object]) -> dict[str, object]`

- [ ] **Step 1: Write failing tests for successful update and backup**

Create `tests/test_config_management.py`:

```python
from pathlib import Path

import pytest

from integration_app.api.config_management import ConfigUpdateError, update_connection_config


def _write_config(path: Path) -> None:
    path.write_text(
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
    protocol: ftp
    host: ftp.example.test
    port: 21
    username: user
    password_env: LAB_X_PASSWORD
    source_dir: ./inbox
    remote_dir: /inbound
    file_pattern: "*.txt"
    sent_dir: Enviados
    error_dir: Erros
    duplicate_policy: report_only
    confirm_remote_processing: true
""",
        encoding="utf-8",
    )


def test_update_connection_config_creates_backup_and_updates_allowed_fields(tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    _write_config(config_path)

    result = update_connection_config(
        config_path,
        "laboratorio_x",
        {
            "enabled": False,
            "source_dir": "C:\\Edi\\Send",
            "remote_dir": "/FACT/Aurovitas/",
            "file_pattern": "*.XML",
            "duplicate_policy": "move_to_duplicates",
            "confirm_remote_processing": False,
        },
    )

    text = config_path.read_text(encoding="utf-8")
    backups = list((tmp_path / "config.backups").glob("config-*.yaml"))
    assert result["connection_name"] == "laboratorio_x"
    assert result["updated"] is True
    assert backups
    assert "enabled: false" in text
    assert "C:\\Edi\\Send" in text
    assert "remote_dir: /FACT/Aurovitas/" in text
    assert "file_pattern: '*.XML'" in text or 'file_pattern: "*.XML"' in text
    assert "duplicate_policy: move_to_duplicates" in text
    assert "confirm_remote_processing: false" in text
    assert "password_env: LAB_X_PASSWORD" in text
```

- [ ] **Step 2: Write failing tests for blocked and invalid updates**

Append to `tests/test_config_management.py`:

```python
def test_update_connection_config_rejects_sensitive_fields(tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    _write_config(config_path)

    with pytest.raises(ConfigUpdateError) as exc:
        update_connection_config(config_path, "laboratorio_x", {"password_env": "NEW_SECRET"})

    assert exc.value.status_code == 400
    assert "not allowed" in str(exc.value)
    assert "NEW_SECRET" not in config_path.read_text(encoding="utf-8")


def test_update_connection_config_rejects_unknown_connection(tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    _write_config(config_path)

    with pytest.raises(ConfigUpdateError) as exc:
        update_connection_config(config_path, "missing", {"enabled": False})

    assert exc.value.status_code == 404


def test_update_connection_config_keeps_original_when_validation_fails(tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    _write_config(config_path)
    original = config_path.read_text(encoding="utf-8")

    with pytest.raises(ConfigUpdateError):
        update_connection_config(config_path, "laboratorio_x", {"duplicate_policy": "invalid"})

    assert config_path.read_text(encoding="utf-8") == original
```

- [ ] **Step 3: Run tests and verify they fail**

Run:

```powershell
python -m pytest tests/test_config_management.py -v
```

Expected: FAIL because `integration_app.api.config_management` does not exist.

- [ ] **Step 4: Implement config management**

Create `src/integration_app/api/config_management.py`:

```python
from __future__ import annotations

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from integration_app.config import load_config


ALLOWED_CONNECTION_FIELDS = {
    "enabled",
    "source_dir",
    "remote_dir",
    "file_pattern",
    "duplicate_policy",
    "confirm_remote_processing",
}

BLOCKED_CONNECTION_FIELDS = {
    "password_env",
    "private_key_path",
    "private_key_passphrase_env",
    "username",
    "host",
    "port",
    "protocol",
}


class ConfigUpdateError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def update_connection_config(config_path: Path, connection_name: str, updates: dict[str, object]) -> dict[str, object]:
    config_path = config_path.resolve()
    raw = _load_raw_config(config_path)
    connections = raw.get("connections")
    if not isinstance(connections, list):
        raise ConfigUpdateError("Invalid config: connections must be a list")
    _validate_update_fields(updates)
    connection = _find_connection(connections, connection_name)
    for key, value in updates.items():
        connection[key] = value
    backup_path = _backup_config(config_path)
    tmp_path = config_path.with_suffix(config_path.suffix + ".tmp")
    try:
        tmp_path.write_text(yaml.safe_dump(raw, sort_keys=False, allow_unicode=False), encoding="utf-8")
        load_config(tmp_path)
        os.replace(tmp_path, config_path)
    except Exception as exc:
        if tmp_path.exists():
            tmp_path.unlink()
        raise ConfigUpdateError(f"Invalid updated config: {exc}") from exc
    return {"connection_name": connection_name, "updated": True, "backup_path": str(backup_path)}


def _load_raw_config(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        raise ConfigUpdateError("Config file not found", status_code=404)
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ConfigUpdateError("Invalid config root")
    return raw


def _validate_update_fields(updates: dict[str, object]) -> None:
    for key in updates:
        if key in BLOCKED_CONNECTION_FIELDS or key not in ALLOWED_CONNECTION_FIELDS:
            raise ConfigUpdateError(f"Field not allowed: {key}")


def _find_connection(connections: list[object], connection_name: str) -> dict[str, Any]:
    for connection in connections:
        if isinstance(connection, dict) and connection.get("name") == connection_name:
            return connection
    raise ConfigUpdateError(f"Connection not found: {connection_name}", status_code=404)


def _backup_config(config_path: Path) -> Path:
    backup_dir = config_path.parent / "config.backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = backup_dir / f"config-{timestamp}.yaml"
    counter = 1
    while backup_path.exists():
        backup_path = backup_dir / f"config-{timestamp}-{counter}.yaml"
        counter += 1
    shutil.copy2(config_path, backup_path)
    return backup_path
```

- [ ] **Step 5: Run tests and verify they pass**

Run:

```powershell
python -m pytest tests/test_config_management.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add src/integration_app/api/config_management.py tests/test_config_management.py
git commit -m "feat: add safe config update module"
```

---

### Task 2: Add Controlled Config Update API

**Files:**
- Modify: `src/integration_app/api/app.py`
- Test: `tests/test_api_app.py`

**Interfaces:**
- Consumes: `update_connection_config(config_path: Path, connection_name: str, updates: dict[str, object]) -> dict[str, object]`
- Produces: `PATCH /config/connections/{name}`

- [ ] **Step 1: Write failing endpoint tests**

Append to `tests/test_api_app.py`:

```python
def test_patch_config_connection_updates_existing_connection(tmp_path: Path):
    db_path = tmp_path / "integration.db"
    SQLiteStore(db_path).initialize()
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
    protocol: ftp
    host: ftp.example.test
    port: 21
    username: user
    password_env: LAB_X_PASSWORD
    source_dir: ./inbox
    remote_dir: /inbound
    file_pattern: "*.txt"
    sent_dir: Enviados
    error_dir: Erros
    duplicate_policy: report_only
    confirm_remote_processing: true
""",
        encoding="utf-8",
    )
    app = create_app(db_path, tmp_path / "reports", config_path=config_path)

    response = TestClient(app).patch("/config/connections/laboratorio_x", json={"enabled": False})

    assert response.status_code == 200
    assert response.json()["updated"] is True
    assert "enabled: false" in config_path.read_text(encoding="utf-8")


def test_patch_config_connection_rejects_sensitive_fields(tmp_path: Path):
    db_path = tmp_path / "integration.db"
    SQLiteStore(db_path).initialize()
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
    protocol: ftp
    host: ftp.example.test
    port: 21
    username: user
    source_dir: ./inbox
    remote_dir: /inbound
    file_pattern: "*.txt"
""",
        encoding="utf-8",
    )
    app = create_app(db_path, tmp_path / "reports", config_path=config_path)

    response = TestClient(app).patch("/config/connections/laboratorio_x", json={"host": "evil.example"})

    assert response.status_code == 400
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
python -m pytest tests/test_api_app.py -v
```

Expected: FAIL because `PATCH /config/connections/{name}` is missing.

- [ ] **Step 3: Implement endpoint**

Modify `src/integration_app/api/app.py`:

```python
from fastapi import Body, FastAPI, HTTPException, Query

from integration_app.api.config_management import ConfigUpdateError, update_connection_config
```

Add near the config summary endpoint:

```python
    @app.patch("/config/connections/{connection_name}")
    def update_config_connection(connection_name: str, updates: dict[str, object] = Body(...)) -> dict[str, object]:
        try:
            return update_connection_config(config_path, connection_name, updates)
        except ConfigUpdateError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
```

- [ ] **Step 4: Run tests and verify they pass**

Run:

```powershell
python -m pytest tests/test_api_app.py tests/test_config_management.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/integration_app/api/app.py tests/test_api_app.py
git commit -m "feat: add controlled config update endpoint"
```

---

### Task 3: Add Dashboard Toggle Action

**Files:**
- Modify: `src/integration_app/api/static/dashboard.js`
- Modify: `src/integration_app/api/static/dashboard.css`
- Test: `tests/test_api_app.py`

**Interfaces:**
- Consumes: `PATCH /config/connections/{name}`
- Produces: activate/deactivate button in the Configuracao list.

- [ ] **Step 1: Write failing dashboard contract tests**

Append assertions to `test_dashboard_javascript_uses_existing_readonly_endpoints` in `tests/test_api_app.py`:

```python
    assert "toggleConnectionEnabled" in javascript
    assert "method: \"PATCH\"" in javascript
    assert "fetchConfigSummary()" in javascript
```

Append assertions to `test_dashboard_assets_include_operational_alert_styles`:

```python
    assert ".config-action" in css
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
python -m pytest tests/test_api_app.py -v
```

Expected: FAIL because the dashboard action is missing.

- [ ] **Step 3: Implement dashboard toggle**

Modify `renderConfigSummary()` in `src/integration_app/api/static/dashboard.js` so each row includes a button:

```javascript
    const actionLabel = connection.enabled ? "Desactivar" : "Activar";
    row.innerHTML = `
      <div>
        <strong>${escapeHtml(connection.name || "")}</strong>
        <small>${escapeHtml(connection.protocol || "")} | ${connection.enabled ? "Activo" : "Inactivo"} | ${escapeHtml(connection.file_pattern || "")}</small>
        <small>${escapeHtml(connection.source_dir || "")} -> ${escapeHtml(connection.remote_dir || "")}</small>
      </div>
      <button class="config-action" type="button">${actionLabel}</button>
    `;
    row.querySelector("button").addEventListener("click", () => toggleConnectionEnabled(connection.name, !connection.enabled));
```

Add helper:

```javascript
async function toggleConnectionEnabled(connectionName, enabled) {
  try {
    await patchJson(`/config/connections/${encodeURIComponent(connectionName)}`, { enabled });
    await fetchConfigSummary();
  } catch (error) {
    showError("config-error", error);
  }
}

async function patchJson(url, payload) {
  const response = await fetch(url, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}
```

Modify `src/integration_app/api/static/dashboard.css`:

```css
.config-action {
  justify-self: end;
}
```

- [ ] **Step 4: Run tests and verify they pass**

Run:

```powershell
python -m pytest tests/test_api_app.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/integration_app/api/static/dashboard.js src/integration_app/api/static/dashboard.css tests/test_api_app.py
git commit -m "feat: toggle connections from dashboard"
```

---

### Task 4: Document And Verify

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: dashboard Configuracao section and `PATCH /config/connections/{name}`.
- Produces: documented safety behaviour.

- [ ] **Step 1: Update README**

Add to the API/dashboard documentation:

```markdown
Na secao `Configuracao`, o dashboard permite activar/desactivar ligacoes existentes. Antes de alterar `config.yaml`, a aplicacao cria backup em `config.backups/`, valida a configuracao resultante e rejeita campos sensiveis como passwords, host, username, port e protocolo.
```

- [ ] **Step 2: Run focused tests**

Run:

```powershell
python -m pytest tests/test_config_management.py tests/test_api_app.py tests/test_api_cli.py -v
```

Expected: PASS.

- [ ] **Step 3: Run full test suite**

Run:

```powershell
python -m pytest -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

```powershell
git add README.md
git commit -m "docs: document controlled config updates"
```

---

## Final Verification

- [ ] Run full test suite:

```powershell
python -m pytest -v
```

Expected: PASS.

- [ ] Check git status:

```powershell
git status --short
```

Expected: clean working tree.
