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
