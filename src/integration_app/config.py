from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from yaml import YAMLError

from integration_app.models import AppConfig, AppPaths, ConnectionConfig, DefaultsConfig


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    config_text = config_path.read_text(encoding="utf-8")
    try:
        raw = yaml.safe_load(config_text)
    except YAMLError:
        raw = yaml.safe_load(config_text.replace("\\", "/"))
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
            generix_storage_root=Path(_optional_str(app_raw, "generix_storage_root") or "") if _optional_str(app_raw, "generix_storage_root") else None,
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
        duplicate_policy=_duplicate_policy(raw),
        schedule_enabled=_optional_bool(raw, "schedule_enabled", False),
        schedule_frequency=str(raw.get("schedule_frequency", "daily")),
        schedule_interval=_required_int(raw, "schedule_interval") if raw.get("schedule_interval") else 1,
        schedule_hour=_required_int(raw, "schedule_hour") if raw.get("schedule_hour") else 0,
        schedule_minute=_required_int(raw, "schedule_minute") if raw.get("schedule_minute") else 0,
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


def _duplicate_policy(raw: dict[str, Any]) -> str:
    value = raw.get("duplicate_policy", "report_only")
    if value not in {"report_only", "move_to_duplicates"}:
        raise ValueError(f"Unsupported duplicate_policy: {value}")
    return value


def _required_int(raw: dict[str, Any], key: str) -> int:
    value = raw.get(key)
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"{key} must be a non-negative integer")
    return value
