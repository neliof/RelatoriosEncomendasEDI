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
