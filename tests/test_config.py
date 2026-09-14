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


@pytest.mark.parametrize("field", ["enabled", "confirm_remote_processing"])
def test_load_config_rejects_non_boolean_connection_flags(tmp_path: Path, field: str):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        f"""
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
    source_dir: ./inbox
    remote_dir: /inbound
    file_pattern: "*.edi"
    {field}: "false"
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=f"{field} must be a boolean"):
        load_config(config_path)


@pytest.mark.parametrize("field", ["password_env", "private_key_passphrase_env"])
def test_load_config_rejects_non_string_optional_env_fields(tmp_path: Path, field: str):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        f"""
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
    source_dir: ./inbox
    remote_dir: /inbound
    file_pattern: "*.edi"
    {field}: 123
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=f"{field} must be a string when provided"):
        load_config(config_path)
