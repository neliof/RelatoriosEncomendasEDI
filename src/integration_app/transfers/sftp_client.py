from __future__ import annotations

from pathlib import Path
from typing import Any

from integration_app.models import ConnectionConfig


class SFTPTransferClient:
    def __init__(self, connection: ConnectionConfig):
        self.connection = connection
        self.transport: Any | None = None
        self.client: Any | None = None

    def connect(self) -> None:
        import paramiko

        transport = paramiko.Transport((self.connection.host, self.connection.port))
        password = self.connection.resolve_password()
        if self.connection.private_key_path is not None:
            passphrase = None
            if self.connection.private_key_passphrase_env:
                import os
                passphrase = os.environ.get(self.connection.private_key_passphrase_env)
            key = paramiko.RSAKey.from_private_key_file(str(self.connection.private_key_path), password=passphrase)
            transport.connect(username=self.connection.username, pkey=key)
        else:
            transport.connect(username=self.connection.username, password=password)
        self.transport = transport
        self.client = paramiko.SFTPClient.from_transport(transport)

    def upload(self, local_path: Path, remote_path: str) -> None:
        if self.client is None:
            raise RuntimeError("SFTP client is not connected")
        self.client.put(str(local_path), remote_path)

    def exists(self, remote_path: str) -> bool:
        if self.client is None:
            raise RuntimeError("SFTP client is not connected")
        try:
            self.client.stat(remote_path)
            return True
        except FileNotFoundError:
            return False

    def close(self) -> None:
        if self.client is not None:
            self.client.close()
            self.client = None
        if self.transport is not None:
            self.transport.close()
            self.transport = None
