from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from integration_app.api.config_management import (
    ConfigUpdateError,
    add_connection_config,
    delete_connection_config,
    update_connection_config,
)


def test_update_connection_config_creates_backup_and_updates_allowed_fields(tmp_path: Path):
    config_path = _write_config(tmp_path)

    result = update_connection_config(
        config_path,
        "laboratorio_x",
        {
            "enabled": False,
            "source_dir": "./entrada",
            "remote_dir": "/processed",
            "file_pattern": "*.xml",
            "duplicate_policy": "move_to_duplicates",
            "confirm_remote_processing": False,
        },
    )

    assert result["connection_name"] == "laboratorio_x"
    assert result["updated"] is True
    backups = list((tmp_path / "config.backups").glob("config-*.yaml"))
    assert len(backups) == 1

    updated = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    connection = updated["connections"][0]
    assert connection["enabled"] is False
    assert connection["source_dir"] == "./entrada"
    assert connection["remote_dir"] == "/processed"
    assert connection["file_pattern"] == "*.xml"
    assert connection["duplicate_policy"] == "move_to_duplicates"
    assert connection["confirm_remote_processing"] is False
    assert connection["password_env"] == "LAB_X_PASSWORD"


def test_update_connection_config_rejects_sensitive_fields(tmp_path: Path):
    config_path = _write_config(tmp_path)

    with pytest.raises(ConfigUpdateError) as exc_info:
        update_connection_config(
            config_path,
            "laboratorio_x",
            {"password_env": "ATTEMPTED_SECRET"},
        )

    assert exc_info.value.status_code == 400
    assert "ATTEMPTED_SECRET" not in config_path.read_text(encoding="utf-8")


def test_update_connection_config_rejects_unknown_connection(tmp_path: Path):
    config_path = _write_config(tmp_path)

    with pytest.raises(ConfigUpdateError) as exc_info:
        update_connection_config(config_path, "missing_connection", {"enabled": False})

    assert exc_info.value.status_code == 404


def test_update_connection_config_keeps_original_when_validation_fails(tmp_path: Path):
    config_path = _write_config(tmp_path)
    original_text = config_path.read_text(encoding="utf-8")

    with pytest.raises(ConfigUpdateError):
        update_connection_config(
            config_path,
            "laboratorio_x",
            {"duplicate_policy": "invalid_policy"},
        )

    assert config_path.read_text(encoding="utf-8") == original_text


def test_add_connection_config_creates_backup_and_adds_valid_connection(tmp_path: Path):
    config_path = _write_config(tmp_path)

    result = add_connection_config(
        config_path,
        {
            "name": "nova_ligacao",
            "enabled": True,
            "flow_type": "generic",
            "protocol": "ftp",
            "host": "ftp.example.test",
            "port": 21,
            "username": "ftp_user",
            "password_env": "NOVA_PASSWORD",
            "source_dir": "./send",
            "remote_dir": "/inbound",
            "file_pattern": "*.txt",
            "sent_dir": "Enviados",
            "error_dir": "Erros",
            "duplicate_policy": "report_only",
            "confirm_remote_processing": True,
        },
    )

    assert result["connection_name"] == "nova_ligacao"
    assert result["created"] is True
    backups = list((tmp_path / "config.backups").glob("config-*.yaml"))
    assert len(backups) == 1
    updated = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert [item["name"] for item in updated["connections"]] == ["laboratorio_x", "nova_ligacao"]


def test_add_connection_config_rejects_duplicate_name_without_changing_file(tmp_path: Path):
    config_path = _write_config(tmp_path)
    original_text = config_path.read_text(encoding="utf-8")

    with pytest.raises(ConfigUpdateError) as exc_info:
        add_connection_config(
            config_path,
            {
                "name": "laboratorio_x",
                "protocol": "ftp",
                "host": "ftp.example.test",
                "port": 21,
                "username": "ftp_user",
                "source_dir": "./send",
                "remote_dir": "/inbound",
            },
        )

    assert exc_info.value.status_code == 409
    assert config_path.read_text(encoding="utf-8") == original_text


def test_delete_connection_config_creates_backup_and_removes_connection(tmp_path: Path):
    config_path = _write_config(tmp_path)
    add_connection_config(
        config_path,
        {
            "name": "nova_ligacao",
            "protocol": "ftp",
            "host": "ftp.example.test",
            "port": 21,
            "username": "ftp_user",
            "source_dir": "./send",
            "remote_dir": "/inbound",
        },
    )

    result = delete_connection_config(config_path, "nova_ligacao")

    assert result["connection_name"] == "nova_ligacao"
    assert result["deleted"] is True
    backups = list((tmp_path / "config.backups").glob("config-*.yaml"))
    assert len(backups) == 2
    updated = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert [item["name"] for item in updated["connections"]] == ["laboratorio_x"]


def test_delete_connection_config_rejects_unknown_connection_without_changing_file(tmp_path: Path):
    config_path = _write_config(tmp_path)
    original_text = config_path.read_text(encoding="utf-8")

    with pytest.raises(ConfigUpdateError) as exc_info:
        delete_connection_config(config_path, "missing")

    assert exc_info.value.status_code == 404
    assert config_path.read_text(encoding="utf-8") == original_text


def _write_config(tmp_path: Path) -> Path:
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
    username: lab_user
    password_env: LAB_X_PASSWORD
    source_dir: ./inbox
    remote_dir: /inbound
    file_pattern: "*.edi"
    duplicate_policy: report_only
    confirm_remote_processing: true
""".lstrip(),
        encoding="utf-8",
    )
    return config_path
