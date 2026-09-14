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
        enabled=_optional_bool(raw, "enabled", True),
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
        password_env=_optional_str(raw, "password_env"),
        private_key_path=Path(raw["private_key_path"]) if raw.get("private_key_path") else None,
        private_key_passphrase_env=_optional_str(raw, "private_key_passphrase_env"),
        confirm_remote_processing=_optional_bool(raw, "confirm_remote_processing", True),
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


def _optional_str(raw: dict[str, Any], key: str) -> str | None:
    value = raw.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string when provided")
    return value


def _optional_bool(raw: dict[str, Any], key: str, default: bool) -> bool:
    value = raw.get(key, default)
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be a boolean")
    return value


def _required_int(raw: dict[str, Any], key: str) -> int:
    value = raw.get(key)
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"{key} must be a non-negative integer")
    return value
