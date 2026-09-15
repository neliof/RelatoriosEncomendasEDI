from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


GLN_PATTERN = re.compile(r"PT\d+")


@dataclass(frozen=True)
class GenerixEdiRecord:
    path: Path
    cab_line: str | None
    detail_count: int
    has_total: bool
    gln_codes: list[str]
    origin_name: str | None


def parse_edi_file(path: Path) -> GenerixEdiRecord:
    lines = _read_text(path).splitlines()
    cab_line = next((line.rstrip() for line in lines if line.startswith("CAB")), None)
    detail_count = sum(1 for line in lines if line.startswith("DET"))
    has_total = any(line.startswith("TOT") for line in lines)
    gln_codes = _unique(GLN_PATTERN.findall(cab_line or ""))
    return GenerixEdiRecord(
        path=path,
        cab_line=cab_line,
        detail_count=detail_count,
        has_total=has_total,
        gln_codes=gln_codes,
        origin_name=_extract_origin_name(cab_line),
    )


def _extract_origin_name(cab_line: str | None) -> str | None:
    if not cab_line:
        return None
    without_glns = GLN_PATTERN.sub(" ", cab_line)
    for part in re.split(r"\s{2,}", without_glns):
        candidate = _clean_name(part)
        if _looks_like_name(candidate):
            return candidate
    return None


def _clean_name(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" -")


def _looks_like_name(value: str) -> bool:
    if value.startswith("CAB") or value.startswith("PT"):
        return False
    alpha_count = sum(1 for character in value if character.isalpha())
    return alpha_count >= 3


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result


def _read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8-sig", errors="replace")
