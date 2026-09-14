from __future__ import annotations

from ftplib import FTP
from pathlib import Path, PurePosixPath

from integration_app.models import ConnectionConfig


class FTPTransferClient:
    def __init__(self, connection: ConnectionConfig):
        self.connection = connection
        self.client: FTP | None = None

    def connect(self) -> None:
        client = FTP()
        client.connect(self.connection.host, self.connection.port, timeout=30)
        client.login(self.connection.username, self.connection.resolve_password() or "")
        self.client = client

    def upload(self, local_path: Path, remote_path: str) -> None:
        if self.client is None:
            raise RuntimeError("FTP client is not connected")
        remote = PurePosixPath(remote_path)
        self.client.cwd(str(remote.parent))
        with local_path.open("rb") as handle:
            self.client.storbinary(f"STOR {remote.name}", handle)

    def exists(self, remote_path: str) -> bool:
        if self.client is None:
            raise RuntimeError("FTP client is not connected")
        remote = PurePosixPath(remote_path)
        current = self.client.pwd()
        try:
            self.client.cwd(str(remote.parent))
            return remote.name in self.client.nlst()
        finally:
            self.client.cwd(current)

    def close(self) -> None:
        if self.client is not None:
            self.client.quit()
            self.client = None
