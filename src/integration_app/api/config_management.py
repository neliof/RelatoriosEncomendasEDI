from __future__ import annotations

import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import yaml

from integration_app.config import load_config


ALLOWED_FIELDS = {
    "enabled",
    "source_dir",
    "remote_dir",
    "file_pattern",
    "duplicate_policy",
    "confirm_remote_processing",
}

CREATE_REQUIRED_FIELDS = {
    "name",
    "protocol",
    "host",
    "port",
    "username",
    "source_dir",
    "remote_dir",
}

CREATE_ALLOWED_FIELDS = {
    "name",
    "enabled",
    "flow_type",
    "protocol",
    "host",
    "port",
    "username",
    "password_env",
    "source_dir",
    "remote_dir",
    "file_pattern",
    "sent_dir",
    "error_dir",
    "duplicate_policy",
    "confirm_remote_processing",
}

BLOCKED_FIELDS = {
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


def update_connection_config(
    config_path: Path,
    connection_name: str,
    updates: dict[str, object],
) -> dict[str, object]:
    config_path = Path(config_path)
    if not config_path.exists():
        raise ConfigUpdateError("Configuration file not found", status_code=404)

    _reject_unsupported_fields(updates)
    config = _load_yaml(config_path)
    connection = _find_connection(config, connection_name)

    connection.update(updates)
    tmp_path = _candidate_path(config_path)
    try:
        tmp_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        load_config(tmp_path)
        backup_path = _backup_config(config_path)
        os.replace(tmp_path, config_path)
    except Exception as exc:
        tmp_path.unlink(missing_ok=True)
        if isinstance(exc, ConfigUpdateError):
            raise
        raise ConfigUpdateError("Invalid configuration update", status_code=400) from exc

    return {
        "connection_name": connection_name,
        "updated": True,
        "backup_path": str(backup_path),
    }


def add_connection_config(config_path: Path, connection: dict[str, object]) -> dict[str, object]:
    config_path = Path(config_path)
    if not config_path.exists():
        raise ConfigUpdateError("Configuration file not found", status_code=404)

    _validate_create_fields(connection)
    config = _load_yaml(config_path)
    connections = config.get("connections")
    if not isinstance(connections, list):
        raise ConfigUpdateError("connections must be a list", status_code=400)
    connection_name = str(connection["name"])
    if any(isinstance(item, dict) and item.get("name") == connection_name for item in connections):
        raise ConfigUpdateError("Connection already exists", status_code=409)

    connections.append(_connection_defaults(connection))
    backup_path = _write_validated_config(config_path, config)
    return {
        "connection_name": connection_name,
        "created": True,
        "backup_path": str(backup_path),
    }


def _reject_unsupported_fields(updates: dict[str, object]) -> None:
    blocked = BLOCKED_FIELDS.intersection(updates)
    if blocked:
        raise ConfigUpdateError("Field cannot be updated", status_code=400)

    unknown = set(updates).difference(ALLOWED_FIELDS)
    if unknown:
        field = sorted(unknown)[0]
        raise ConfigUpdateError(f"Unknown field: {field}", status_code=400)


def _validate_create_fields(connection: dict[str, object]) -> None:
    unknown = set(connection).difference(CREATE_ALLOWED_FIELDS)
    if unknown:
        raise ConfigUpdateError(f"Unknown field: {sorted(unknown)[0]}", status_code=400)

    missing = [field for field in sorted(CREATE_REQUIRED_FIELDS) if field not in connection]
    if missing:
        raise ConfigUpdateError(f"Missing field: {missing[0]}", status_code=400)


def _connection_defaults(connection: dict[str, object]) -> dict[str, object]:
    created = dict(connection)
    created.setdefault("enabled", True)
    created.setdefault("flow_type", "generic")
    created.setdefault("file_pattern", "*")
    created.setdefault("sent_dir", "Enviados")
    created.setdefault("error_dir", "Erros")
    created.setdefault("duplicate_policy", "report_only")
    created.setdefault("confirm_remote_processing", True)
    return created


def _write_validated_config(config_path: Path, config: dict[str, object]) -> Path:
    tmp_path = _candidate_path(config_path)
    try:
        tmp_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        load_config(tmp_path)
        backup_path = _backup_config(config_path)
        os.replace(tmp_path, config_path)
    except Exception as exc:
        tmp_path.unlink(missing_ok=True)
        if isinstance(exc, ConfigUpdateError):
            raise
        raise ConfigUpdateError("Invalid configuration update", status_code=400) from exc
    return backup_path


def _load_yaml(config_path: Path) -> dict[str, object]:
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ConfigUpdateError("Configuration root must be a mapping", status_code=400)
    return raw


def _find_connection(config: dict[str, object], connection_name: str) -> dict[str, object]:
    connections = config.get("connections")
    if not isinstance(connections, list):
        raise ConfigUpdateError("connections must be a list", status_code=400)

    for connection in connections:
        if isinstance(connection, dict) and connection.get("name") == connection_name:
            return connection
    raise ConfigUpdateError("Connection not found", status_code=404)


def _candidate_path(config_path: Path) -> Path:
    return config_path.with_name(f".{config_path.name}.{uuid4().hex}.tmp")


def _backup_config(config_path: Path) -> Path:
    backup_dir = config_path.parent / "config.backups"
    backup_dir.mkdir(exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    backup_path = backup_dir / f"config-{timestamp}.yaml"
    shutil.copy2(config_path, backup_path)
    return backup_path
