from __future__ import annotations

import csv
import json
from pathlib import Path

from openpyxl import Workbook

from integration_app.order_edi import OrderEdiRecord, empty_order_edi_record, order_duplicate_key, parse_order_edi_file
from integration_app.order_xml import OrderXmlRecord, empty_order_xml_record, order_xml_duplicate_key, parse_order_xml_file
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
    "edi_tipo_mensagem",
    "edi_remetente_nome",
    "edi_remetente_gln",
    "edi_fornecedor_nome",
    "edi_fornecedor_gln",
    "edi_serie_encomenda",
    "edi_numero_encomenda",
    "edi_numero_encomenda_conteudo",
    "edi_linhas_encomenda",
    "edi_duplicate_key",
    "edi_duplicate_status",
    "xml_buyer_name",
    "xml_buyer_vat",
    "xml_buyer_ean",
    "xml_seller_vat",
    "xml_seller_name",
    "xml_seller_ean",
    "xml_seller_canal",
    "xml_order_type",
    "xml_order_number",
    "xml_buyer_order_number",
    "xml_order_date",
    "xml_linhas_encomenda",
    "xml_duplicate_key",
    "xml_duplicate_status",
]

SUMMARY_COLUMNS = [
    "report_date",
    "connection_name",
    "flow_type",
    "protocol",
    "supplier_name",
    "total_files",
    "sent_count",
    "confirmed_count",
    "duplicate_count",
    "failed_count",
    "pending_count",
    "unknown_count",
    "total_order_lines",
]


def export_reports(store: SQLiteStore, report_dir: Path, run_id: str) -> list[Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    rows = _mark_duplicates([_enrich_row(row) for row in store.report_rows()])
    summary_rows = _build_daily_summary(rows)
    csv_path = report_dir / f"{run_id}.csv"
    json_path = report_dir / f"{run_id}.json"
    xlsx_path = report_dir / f"{run_id}.xlsx"
    summary_csv_path = report_dir / f"{run_id}-summary.csv"
    summary_json_path = report_dir / f"{run_id}-summary.json"
    summary_xlsx_path = report_dir / f"{run_id}-summary.xlsx"
    _write_csv(csv_path, rows)
    _write_json(json_path, rows)
    _write_xlsx(xlsx_path, rows)
    _write_csv(summary_csv_path, summary_rows, SUMMARY_COLUMNS)
    _write_json(summary_json_path, summary_rows)
    _write_xlsx(summary_xlsx_path, summary_rows, SUMMARY_COLUMNS, "Daily Summary")
    return [csv_path, json_path, xlsx_path, summary_csv_path, summary_json_path, summary_xlsx_path]


def _write_csv(path: Path, rows: list[dict[str, object]], columns: list[str] | None = None) -> None:
    fieldnames = columns or REPORT_COLUMNS
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")


def _write_xlsx(path: Path, rows: list[dict[str, object]], columns: list[str] | None = None, title: str = "Report") -> None:
    fieldnames = columns or REPORT_COLUMNS
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = title
    sheet.append(fieldnames)
    for row in rows:
        sheet.append([row.get(column) for column in fieldnames])
    workbook.save(path)


def _build_daily_summary(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    summary: dict[tuple[str, str, str, str, str], dict[str, object]] = {}
    for row in rows:
        key = (
            _date_part(row.get("detected_at")),
            str(row.get("connection_name") or ""),
            str(row.get("flow_type") or ""),
            str(row.get("protocol") or ""),
            _supplier_name(row),
        )
        if key not in summary:
            report_date, connection_name, flow_type, protocol, supplier_name = key
            summary[key] = {
                "report_date": report_date,
                "connection_name": connection_name,
                "flow_type": flow_type,
                "protocol": protocol,
                "supplier_name": supplier_name,
                "total_files": 0,
                "sent_count": 0,
                "confirmed_count": 0,
                "duplicate_count": 0,
                "failed_count": 0,
                "pending_count": 0,
                "unknown_count": 0,
                "total_order_lines": 0,
            }
        item = summary[key]
        status = str(row.get("status") or "")
        confirmation_status = str(row.get("confirmation_status") or "")
        item["total_files"] = int(item["total_files"]) + 1
        if status in {"sent", "confirmed"}:
            item["sent_count"] = int(item["sent_count"]) + 1
        if status == "confirmed":
            item["confirmed_count"] = int(item["confirmed_count"]) + 1
        elif status == "sent":
            pass
        elif status == "duplicate":
            item["duplicate_count"] = int(item["duplicate_count"]) + 1
        elif status == "failed":
            item["failed_count"] = int(item["failed_count"]) + 1
        else:
            item["unknown_count"] = int(item["unknown_count"]) + 1
        if confirmation_status == "pending":
            item["pending_count"] = int(item["pending_count"]) + 1
        item["total_order_lines"] = int(item["total_order_lines"]) + _order_lines(row)
    return [summary[key] for key in sorted(summary)]


def _enrich_row(row: dict[str, object]) -> dict[str, object]:
    enriched = dict(row)
    edi_record = _parse_order_edi_for_row(row)
    xml_record = _parse_order_xml_for_row(row)
    enriched.update(
        {
            "edi_tipo_mensagem": edi_record.tipo_mensagem,
            "edi_remetente_nome": edi_record.remetente_nome,
            "edi_remetente_gln": edi_record.remetente_gln,
            "edi_fornecedor_nome": edi_record.fornecedor_nome,
            "edi_fornecedor_gln": edi_record.fornecedor_gln,
            "edi_serie_encomenda": edi_record.serie_encomenda,
            "edi_numero_encomenda": edi_record.numero_encomenda,
            "edi_numero_encomenda_conteudo": edi_record.numero_encomenda_conteudo,
            "edi_linhas_encomenda": edi_record.linhas_encomenda,
            "edi_duplicate_key": order_duplicate_key(edi_record),
            "edi_duplicate_status": "unknown",
            "xml_buyer_name": xml_record.buyer_name,
            "xml_buyer_vat": xml_record.buyer_vat,
            "xml_buyer_ean": xml_record.buyer_ean,
            "xml_seller_vat": xml_record.seller_vat,
            "xml_seller_name": xml_record.seller_name,
            "xml_seller_ean": xml_record.seller_ean,
            "xml_seller_canal": xml_record.seller_canal,
            "xml_order_type": xml_record.order_type,
            "xml_order_number": xml_record.order_number,
            "xml_buyer_order_number": xml_record.buyer_order_number,
            "xml_order_date": xml_record.order_date,
            "xml_linhas_encomenda": xml_record.linhas_encomenda,
            "xml_duplicate_key": order_xml_duplicate_key(xml_record),
            "xml_duplicate_status": "unknown",
        }
    )
    return enriched


def _mark_duplicates(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    _mark_duplicate_status(rows, "edi_duplicate_key", "edi_duplicate_status")
    _mark_duplicate_status(rows, "xml_duplicate_key", "xml_duplicate_status")
    return rows


def _mark_duplicate_status(rows: list[dict[str, object]], key_column: str, status_column: str) -> None:
    seen: set[str] = set()
    for row in rows:
        duplicate_key = row.get(key_column)
        if not duplicate_key:
            row[status_column] = "unknown"
        elif duplicate_key in seen:
            row[status_column] = "duplicate"
        else:
            row[status_column] = "unique"
            seen.add(str(duplicate_key))


def _parse_order_edi_for_row(row: dict[str, object]) -> OrderEdiRecord:
    path = _resolve_order_edi_path(row)
    if path is None or path.suffix.lower() == ".xml":
        return empty_order_edi_record()
    return parse_order_edi_file(path)


def _parse_order_xml_for_row(row: dict[str, object]) -> OrderXmlRecord:
    path = _resolve_order_edi_path(row)
    if path is None or path.suffix.lower() != ".xml":
        return empty_order_xml_record()
    return parse_order_xml_file(path)


def _resolve_order_edi_path(row: dict[str, object]) -> Path | None:
    local_path = row.get("local_path")
    if not isinstance(local_path, str):
        return None
    path = Path(local_path)
    if path.exists():
        return path
    if row.get("status") in {"sent", "confirmed"}:
        sent_path = path.parent / "Enviados" / path.name
        if sent_path.exists():
            return sent_path
    if row.get("status") == "failed":
        error_path = path.parent / "Erros" / path.name
        if error_path.exists():
            return error_path
    if row.get("status") == "duplicate":
        duplicate_path = path.parent / "Duplicados" / path.name
        if duplicate_path.exists():
            return duplicate_path
    return None


def _date_part(value: object) -> str:
    if not isinstance(value, str) or not value:
        return ""
    return value[:10]


def _supplier_name(row: dict[str, object]) -> str:
    edi_supplier = row.get("edi_fornecedor_nome")
    if isinstance(edi_supplier, str) and edi_supplier:
        return edi_supplier
    xml_supplier = row.get("xml_seller_name")
    if isinstance(xml_supplier, str) and xml_supplier:
        return xml_supplier
    return "UNKNOWN"


def _order_lines(row: dict[str, object]) -> int:
    for key in ("edi_linhas_encomenda", "xml_linhas_encomenda"):
        value = row.get(key)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    return 0
