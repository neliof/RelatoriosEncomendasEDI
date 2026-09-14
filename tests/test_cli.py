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


def test_main_generix_report_returns_zero(tmp_path: Path):
    root = tmp_path / "storage" / "cpip_1"
    headers = root / "sent" / "headers"
    headers.mkdir(parents=True)
    (headers / "sample.hdr").write_text(
        "unique-id=NXC-1\nsubject=Encomenda.txt\n[log]\nthe message was PROCESSED\n",
        encoding="utf-8",
    )

    exit_code = main(
        [
            "generix-report",
            "--storage-root",
            str(root),
            "--report-dir",
            str(tmp_path / "reports"),
            "--run-id",
            "manual",
        ]
    )

    assert exit_code == 0
    assert (tmp_path / "reports" / "manual.csv").exists()
    assert (tmp_path / "reports" / "manual.json").exists()
