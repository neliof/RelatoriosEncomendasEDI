from pathlib import Path

import pytest

from integration_app.models import ConnectionConfig
from integration_app.transfers.base import build_transfer_client
from integration_app.transfers.ftp_client import FTPTransferClient
from integration_app.transfers.sftp_client import SFTPTransferClient


def _connection(protocol: str) -> ConnectionConfig:
    return ConnectionConfig(
        name="lab",
        enabled=True,
        flow_type="generic",
        protocol=protocol,
        host="example.test",
        port=22 if protocol == "sftp" else 21,
        username="user",
        source_dir=Path("."),
        remote_dir="/inbound",
        file_pattern="*.edi",
    )


def test_build_transfer_client_returns_ftp_client():
    assert isinstance(build_transfer_client(_connection("ftp")), FTPTransferClient)


def test_build_transfer_client_returns_sftp_client():
    assert isinstance(build_transfer_client(_connection("sftp")), SFTPTransferClient)


def test_build_transfer_client_rejects_unknown_protocol():
    with pytest.raises(ValueError, match="Unsupported protocol: smtp"):
        build_transfer_client(_connection("smtp"))
