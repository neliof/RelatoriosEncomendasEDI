from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


GLN_PATTERN = re.compile(r"PT\d+")
ORDER_REF_PATTERN = re.compile(r"\b[A-Z]+/[A-Z0-9]+/\d+\b")
FILENAME_PATTERN = re.compile(r"^Pedido_EDI_(?P<sender>.+?)_(?P<supplier>.+?)_(?P<series>[A-Za-z0-9]+)-(?P<number>\d+)")


@dataclass(frozen=True)
class OrderEdiRecord:
    tipo_mensagem: str | None
    remetente_nome: str | None
    remetente_gln: str | None
    fornecedor_nome: str | None
    fornecedor_gln: str | None
    serie_encomenda: str | None
    numero_encomenda: str | None
    numero_encomenda_conteudo: str | None
    linhas_encomenda: int


def parse_order_edi_file(path: Path) -> OrderEdiRecord:
    lines = _read_text(path).splitlines()
    first_line = lines[0] if lines else ""
    second_line = lines[1] if len(lines) > 1 else ""
    filename_parts = _parse_filename(path.name)
    return OrderEdiRecord(
        tipo_mensagem=_first_token(first_line),
        remetente_nome=filename_parts.get("sender"),
        remetente_gln=_first_gln(first_line),
        fornecedor_nome=filename_parts.get("supplier"),
        fornecedor_gln=_first_gln(second_line),
        serie_encomenda=filename_parts.get("series"),
        numero_encomenda=filename_parts.get("number"),
        numero_encomenda_conteudo=_first_order_ref(second_line),
        linhas_encomenda=sum(1 for line in lines if line.startswith("D")),
    )


def empty_order_edi_record() -> OrderEdiRecord:
    return OrderEdiRecord(
        tipo_mensagem=None,
        remetente_nome=None,
        remetente_gln=None,
        fornecedor_nome=None,
        fornecedor_gln=None,
        serie_encomenda=None,
        numero_encomenda=None,
        numero_encomenda_conteudo=None,
        linhas_encomenda=0,
    )


def order_duplicate_key(record: OrderEdiRecord) -> str | None:
    parts = [
        record.remetente_gln,
        record.fornecedor_gln,
        record.serie_encomenda,
        record.numero_encomenda,
    ]
    if any(part is None for part in parts):
        return None
    return "|".join(str(part) for part in parts)


def _parse_filename(filename: str) -> dict[str, str]:
    match = FILENAME_PATTERN.match(Path(filename).stem)
    if not match:
        return {}
    return match.groupdict()


def _first_token(line: str) -> str | None:
    parts = line.split()
    return parts[0] if parts else None


def _first_gln(line: str) -> str | None:
    match = GLN_PATTERN.search(line)
    return match.group(0) if match else None


def _first_order_ref(line: str) -> str | None:
    match = ORDER_REF_PATTERN.search(line)
    return match.group(0) if match else None


def _read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8-sig", errors="replace")
