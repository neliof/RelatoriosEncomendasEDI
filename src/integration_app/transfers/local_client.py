from __future__ import annotations

import shutil
from pathlib import Path

from integration_app.models import ConnectionConfig


class LocalTransferClient:
    def __init__(self, connection: ConnectionConfig):
        self.connection = connection
        self.connected = False

    def connect(self) -> None:
        self.connected = True

    def upload(self, local_path: Path, remote_path: str) -> None:
        if not self.connected:
            raise RuntimeError("Not connected")

        source = Path(local_path)
        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source}")

        destination = Path(self.connection.source_dir) / Path(remote_path).name
        destination.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy2(source, destination)

    def exists(self, remote_path: str) -> bool:
        destination = Path(self.connection.source_dir) / Path(remote_path).name
        return destination.exists()

    def close(self) -> None:
        self.connected = False
