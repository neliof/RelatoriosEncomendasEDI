from __future__ import annotations

import argparse
import logging
from datetime import UTC, datetime
from pathlib import Path

from integration_app.config import load_config
from integration_app.core.runner import run_once
from integration_app.logging_setup import configure_json_logging
from integration_app.reports.exporters import export_reports
from integration_app.storage.sqlite_store import SQLiteStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="integration-app")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run-once")
    run_parser.add_argument("--config", required=True)
    args = parser.parse_args(argv)

    if args.command == "run-once":
        return _run_once_command(Path(args.config))
    return 2


def _run_once_command(config_path: Path) -> int:
    config = load_config(config_path)
    configure_json_logging(config.app.log_dir)
    logging.info("Starting integration run")
    store = SQLiteStore(config.app.database_path)
    store.initialize()
    summary = run_once(config, store)
    run_id = datetime.now(UTC).strftime("run-%Y%m%d-%H%M%S")
    export_reports(store, config.app.report_dir, run_id)
    logging.info("Finished integration run: %s", summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
