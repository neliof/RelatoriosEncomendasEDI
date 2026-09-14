from __future__ import annotations

import csv
import json
from pathlib import Path

from integration_app.generix.headers import GenerixHeaderRecord, scan_header_dir


GENERIX_REPORT_COLUMNS = [
    "flow_type",
    "unique_id",
    "subject",
    "date",
    "from",
    "to",
    "message_id",
    "pipe_id",
    "receipt",
    "disposition",
    "processed",
    "body_path",
    "header_path",
    "log_events",
]


def export_header_report(storage_root: Path, report_dir: Path, run_id: str) -> list[Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    records = _scan_storage_root(storage_root)
    rows = [_record_to_row(record) for record in records]
    csv_path = report_dir / f"{run_id}.csv"
    json_path = report_dir / f"{run_id}.json"
    _write_csv(csv_path, rows)
    _write_json(json_path, rows)
    return [csv_path, json_path]


def _scan_storage_root(storage_root: Path) -> list[GenerixHeaderRecord]:
    records: list[GenerixHeaderRecord] = []
    records.extend(scan_header_dir(storage_root / "received" / "headers", flow_type="received"))
    records.extend(scan_header_dir(storage_root / "sent" / "headers", flow_type="sent"))
    return records


def _record_to_row(record: GenerixHeaderRecord) -> dict[str, object]:
    return {
        "flow_type": record.flow_type,
        "unique_id": record.unique_id,
        "subject": record.subject,
        "date": record.date,
        "from": record.message_from,
        "to": record.message_to,
        "message_id": record.message_id,
        "pipe_id": record.pipe_id,
        "receipt": record.receipt,
        "disposition": record.disposition,
        "processed": record.processed,
        "body_path": record.body_path,
        "header_path": str(record.header_path),
        "log_events": "\n".join(record.log_events),
    }


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=GENERIX_REPORT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

