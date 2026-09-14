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
