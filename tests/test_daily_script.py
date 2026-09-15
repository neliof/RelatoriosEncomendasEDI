from pathlib import Path


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
