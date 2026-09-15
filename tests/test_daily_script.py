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
