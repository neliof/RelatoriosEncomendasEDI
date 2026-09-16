from pathlib import Path
import subprocess


def test_daily_script_runs_transfer_then_generix_report():
    script = Path("scripts/run-daily.ps1")

    content = script.read_text(encoding="utf-8")

    assert "$env:PYTHONPATH" in content
    assert "run-once --config" in content
    assert "generix-report --storage-root" in content
    assert "$LASTEXITCODE" in content
    assert "exit $LASTEXITCODE" in content


def test_daily_script_writes_timestamped_log():
    script = Path("scripts/run-daily.ps1")

    content = script.read_text(encoding="utf-8")

    assert "$LogDir" in content
    assert "run-daily-" in content
    assert "Start-Transcript" in content
    assert "Stop-Transcript" in content


def test_daily_script_prefers_project_virtual_environment():
    script = Path("scripts/run-daily.ps1")

    content = script.read_text(encoding="utf-8")

    assert ".venv\\Scripts\\python.exe" in content
    assert "$PythonExe" in content


def test_daily_script_has_configurable_retention_cleanup():
    script = Path("scripts/run-daily.ps1")

    content = script.read_text(encoding="utf-8")

    assert "[int]$RetentionDays = 30" in content
    assert "[switch]$DisableCleanup" in content
    assert "Get-ChildItem -Path $ReportDir" in content
    assert "Get-ChildItem -Path $LogDir" in content
    assert "Remove-Item" in content
    assert "AddDays(-$RetentionDays)" in content


def test_task_scheduler_docs_show_frequency_and_retention_options():
    docs = Path("docs/install-windows-task-scheduler.md")

    content = docs.read_text(encoding="utf-8")

    assert "Repeat task every: 5 minutes" in content
    assert "Repeat task every: 10 minutes" in content
    assert "Repeat task every: 30 minutes" in content
    assert "Repeat task every: 1 hour" in content
    assert "-RetentionDays 60" in content
    assert "-DisableCleanup" in content


def test_install_scheduled_task_dry_run_describes_interval_task():
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            "scripts/install-scheduled-task.ps1",
            "-Schedule",
            "Minutes",
            "-EveryMinutes",
            "10",
            "-DryRun",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "RelatoriosEncomendasEDI_EF" in result.stdout
    assert "run-daily.ps1" in result.stdout
    assert "Every 10 minute(s)" in result.stdout
    assert "RunLevel: Limited" in result.stdout


def test_daily_script_loads_dpapi_secret_before_running_python():
    script = Path("scripts/run-daily.ps1")

    content = script.read_text(encoding="utf-8")

    assert "$SecretDir" in content
    assert "$PasswordEnvName.secret" in content
    assert "ConvertTo-SecureString" in content
    assert "NetworkCredential" in content
    assert "Set-Item -Path \"Env:$PasswordEnvName\"" in content


def test_gitignore_excludes_local_secrets():
    gitignore = Path(".gitignore")

    content = gitignore.read_text(encoding="utf-8")

    assert "secrets/" in content
