from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


FILENAME_PATTERN = re.compile(
    r"^Pedido_EDI_(?P<buyer>.+?)_(?P<buyer_ean>\d+)(?P<series>[A-Za-z0-9]+)-(?P<number>\d+)"
)
SELLER_NAMES_BY_VAT = {
    "PT500043531": "BEIERSDORF PORTUGUESA, LDA.",
}


@dataclass(frozen=True)
class OrderXmlRecord:
    buyer_name: str | None
    buyer_vat: str | None
    buyer_ean: str | None
    seller_vat: str | None
    seller_name: str | None
    seller_ean: str | None
    seller_canal: str | None
    order_type: str | None
    order_number: str | None
    buyer_order_number: str | None
    order_date: str | None
    linhas_encomenda: int


def parse_order_xml_file(path: Path) -> OrderXmlRecord:
    root = ET.fromstring(_read_text(path))
    order = root.find("EOrder")
    filename_parts = _parse_filename(path.name)
    seller_vat = _text(order, "SellerVAT")
    buyer_order_number = _text(order, "ByerOrderNumber")
    order_type = _text(order, "OrderType") or filename_parts.get("series")
    return OrderXmlRecord(
        buyer_name=filename_parts.get("buyer"),
        buyer_vat=_text(order, "BuyerVAT"),
        buyer_ean=_text(order, "BuyerEANCode") or filename_parts.get("buyer_ean"),
        seller_vat=seller_vat,
        seller_name=SELLER_NAMES_BY_VAT.get(seller_vat) if seller_vat else None,
        seller_ean=_text(order, "SellerEANCode"),
        seller_canal=_text(order, "SellerCanal"),
        order_type=order_type,
        order_number=_order_number(buyer_order_number) or filename_parts.get("number"),
        buyer_order_number=buyer_order_number,
        order_date=_text(order, "OrderDate"),
        linhas_encomenda=len(order.findall("BuyOrderItem")) if order is not None else 0,
    )


def empty_order_xml_record() -> OrderXmlRecord:
    return OrderXmlRecord(
        buyer_name=None,
        buyer_vat=None,
        buyer_ean=None,
        seller_vat=None,
        seller_name=None,
        seller_ean=None,
        seller_canal=None,
        order_type=None,
        order_number=None,
        buyer_order_number=None,
        order_date=None,
        linhas_encomenda=0,
    )


def order_xml_duplicate_key(record: OrderXmlRecord) -> str | None:
    parts = [
        record.buyer_ean,
        record.seller_vat,
        record.order_type,
        record.order_number,
    ]
    if any(part is None for part in parts):
        return None
    return "|".join(str(part) for part in parts)


def is_order_xml_path(path: Path) -> bool:
    return path.suffix.lower() == ".xml"


def _parse_filename(filename: str) -> dict[str, str]:
    match = FILENAME_PATTERN.match(Path(filename).stem)
    if not match:
        return {}
    return match.groupdict()


def _text(order: ET.Element | None, tag: str) -> str | None:
    if order is None:
        return None
    value = order.findtext(tag)
    value = value.strip() if value else None
    return value or None


def _order_number(buyer_order_number: str | None) -> str | None:
    if not buyer_order_number:
        return None
    return buyer_order_number.rsplit("/", 1)[-1] or None


def _read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8-sig", errors="replace")
