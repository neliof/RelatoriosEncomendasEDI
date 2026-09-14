import re
from pathlib import Path


def test_interactive_ftp_script_prompts_for_password_without_storing_it():
    script = Path("scripts/test-ftp-interactive.ps1")

    content = script.read_text(encoding="utf-8")

    assert re.search(r"Read-Host\b.*-AsSecureString", content)
    assert "PRIMEIRA_LIGACAO_FTP_PASSWORD" in content
    assert "python -m integration_app.app run-once --config" in content
    assert "PYTHONPATH" in content
