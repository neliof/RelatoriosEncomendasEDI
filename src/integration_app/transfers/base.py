from __future__ import annotations

from pathlib import Path
from typing import Protocol

from integration_app.models import ConnectionConfig


class TransferClient(Protocol):
    def connect(self) -> None:
        ...

    def upload(self, local_path: Path, remote_path: str) -> None:
        ...

    def exists(self, remote_path: str) -> bool:
        ...

    def close(self) -> None:
        ...


def build_transfer_client(connection: ConnectionConfig) -> TransferClient:
    if connection.protocol == "ftp":
        from integration_app.transfers.ftp_client import FTPTransferClient

        return FTPTransferClient(connection)
    if connection.protocol == "sftp":
        from integration_app.transfers.sftp_client import SFTPTransferClient

        return SFTPTransferClient(connection)
    raise ValueError(f"Unsupported protocol: {connection.protocol}")
