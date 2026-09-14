from pathlib import Path

from integration_app.app import main


def test_main_run_once_returns_zero(tmp_path: Path):
    source = tmp_path / "inbox"
    source.mkdir()
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        f"""
app:
  database_path: "{tmp_path / 'data' / 'integration.db'}"
  log_dir: "{tmp_path / 'logs'}"
  report_dir: "{tmp_path / 'reports'}"
defaults:
  stable_after_seconds: 0
  confirmation_timeout_minutes: 120
connections: []
""",
        encoding="utf-8",
    )

    exit_code = main(["run-once", "--config", str(config_path)])

    assert exit_code == 0
    assert (tmp_path / "data" / "integration.db").exists()
    assert any((tmp_path / "reports").glob("*.csv"))
    assert any((tmp_path / "reports").glob("*.json"))
    assert any((tmp_path / "reports").glob("*.xlsx"))
    assert any((tmp_path / "logs").glob("*.jsonl"))
