import re
import subprocess
from pathlib import Path


def test_interactive_ftp_script_prompts_for_password_without_storing_it():
    script = Path("scripts/test-ftp-interactive.ps1")

    content = script.read_text(encoding="utf-8")

    assert re.search(r"Read-Host\b.*-AsSecureString", content)
    assert "PRIMEIRA_LIGACAO_FTP_PASSWORD" in content
    assert "python -m integration_app.app run-once --config" in content
    assert "PYTHONPATH" in content


def test_set_ftp_password_user_script_has_safe_dry_run():
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            "scripts/set-ftp-password-user.ps1",
            "-DryRun",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "PRIMEIRA_LIGACAO_FTP_PASSWORD" in result.stdout
    assert "Target: User environment" in result.stdout
    assert "DryRun: no password was requested or stored." in result.stdout
