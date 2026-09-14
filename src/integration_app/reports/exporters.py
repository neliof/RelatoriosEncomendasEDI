from __future__ import annotations

import csv
import json
from pathlib import Path

from openpyxl import Workbook

from integration_app.storage.sqlite_store import SQLiteStore


REPORT_COLUMNS = [
    "connection_name",
    "flow_type",
    "protocol",
    "local_path",
    "remote_path",
    "status",
    "detected_at",
    "sent_at",
    "confirmation_status",
    "confirmation_checked_at",
    "error_message",
]


def export_reports(store: SQLiteStore, report_dir: Path, run_id: str) -> list[Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    rows = store.report_rows()
    csv_path = report_dir / f"{run_id}.csv"
    json_path = report_dir / f"{run_id}.json"
    xlsx_path = report_dir / f"{run_id}.xlsx"
    _write_csv(csv_path, rows)
    _write_json(json_path, rows)
    _write_xlsx(xlsx_path, rows)
    return [csv_path, json_path, xlsx_path]


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REPORT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")


def _write_xlsx(path: Path, rows: list[dict[str, object]]) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Report"
    sheet.append(REPORT_COLUMNS)
    for row in rows:
        sheet.append([row.get(column) for column in REPORT_COLUMNS])
    workbook.save(path)
