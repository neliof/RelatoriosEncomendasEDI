from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GenerixHeaderRecord:
    flow_type: str
    header_path: Path
    fields: dict[str, str]
    log_events: list[str]

    @property
    def body_path(self) -> str | None:
        return self.fields.get("body-path")

    @property
    def date(self) -> str | None:
        return self.fields.get("date")

    @property
    def disposition(self) -> str | None:
        return self.fields.get("disposition")

    @property
    def message_from(self) -> str | None:
        return self.fields.get("from")

    @property
    def message_id(self) -> str | None:
        return self.fields.get("message-id")

    @property
    def message_to(self) -> str | None:
        return self.fields.get("to")

    @property
    def pipe_id(self) -> str | None:
        return self.fields.get("pipe-id")

    @property
    def receipt(self) -> str | None:
        return self.fields.get("receipt")

    @property
    def subject(self) -> str | None:
        return self.fields.get("subject")

    @property
    def unique_id(self) -> str | None:
        return self.fields.get("unique-id")

    @property
    def processed(self) -> bool:
        disposition = self.disposition or ""
        if "processed" in disposition.lower():
            return True
        return any("processed" in event.lower() for event in self.log_events)


def parse_header_file(path: Path, flow_type: str) -> GenerixHeaderRecord:
    fields: dict[str, str] = {}
    log_events: list[str] = []
    in_log = False

    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.lower() == "[log]":
            in_log = True
            continue
        if in_log:
            log_events.append(line)
            continue
        key, separator, value = line.partition("=")
        if separator:
            fields[key.strip().lower()] = value.strip()

    return GenerixHeaderRecord(
        flow_type=flow_type,
        header_path=path,
        fields=fields,
        log_events=log_events,
    )


def scan_header_dir(path: Path, flow_type: str) -> list[GenerixHeaderRecord]:
    if not path.exists():
        return []
    return [parse_header_file(header_path, flow_type) for header_path in sorted(path.glob("*.hdr"))]

