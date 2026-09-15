from __future__ import annotations

import argparse
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from integration_app.config import load_config
from integration_app.core.runner import run_once
from integration_app.generix.reports import export_header_report, summarize_rows
from integration_app.logging_setup import configure_json_logging
from integration_app.reports.exporters import export_reports
from integration_app.storage.sqlite_store import SQLiteStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="integration-app")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run-once")
    run_parser.add_argument("--config", required=True)
    generix_parser = subparsers.add_parser("generix-report")
    generix_parser.add_argument("--storage-root", required=True)
    generix_parser.add_argument("--report-dir", required=True)
    generix_parser.add_argument("--run-id")
    args = parser.parse_args(argv)

    if args.command == "run-once":
        return _run_once_command(Path(args.config))
    if args.command == "generix-report":
        return _generix_report_command(
            storage_root=Path(args.storage_root),
            report_dir=Path(args.report_dir),
            run_id=args.run_id,
        )
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


def _generix_report_command(storage_root: Path, report_dir: Path, run_id: str | None) -> int:
    report_id = run_id or datetime.now(UTC).strftime("generix-%Y%m%d-%H%M%S")
    written = export_header_report(storage_root, report_dir, report_id)
    for path in written:
        print(path)
    rows = json.loads(written[1].read_text(encoding="utf-8"))
    summary = summarize_rows(rows)
    print(f"Total: {summary['total']}")
    print(f"OK: {summary['ok']}")
    print(f"Warnings: {summary['warnings']}")
    print(f"Errors: {summary['errors']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
