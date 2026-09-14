from pathlib import Path

from integration_app.generix.headers import parse_header_file, scan_header_dir


def test_parse_header_file_returns_fields_and_log_events(tmp_path: Path):
    header_path = tmp_path / "NXC-123.hdr"
    header_path.write_text(
        """body-path=C:\\Generix\\sent\\data\\NXC-123.txt
content-type=application/txt
date=Sat, 12 Sep 2026 10:53:17 +0100
from=influe@netixone.com.pt
to=fch@netixone.com.pt
message-id=<abc@PCGENERIX>
receipt=ON
subject=Encomenda_20260912_105317.txt
unique-id=NXC-123

[log]
2026-09-12 10:53:18 the message was uploaded
2026-09-12 10:53:19 the message was PROCESSED
""",
        encoding="utf-8",
    )

    record = parse_header_file(header_path, flow_type="sent")

    assert record.flow_type == "sent"
    assert record.header_path == header_path
    assert record.body_path == "C:\\Generix\\sent\\data\\NXC-123.txt"
    assert record.unique_id == "NXC-123"
    assert record.subject == "Encomenda_20260912_105317.txt"
    assert record.message_from == "influe@netixone.com.pt"
    assert record.message_to == "fch@netixone.com.pt"
    assert record.disposition is None
    assert record.log_events == [
        "2026-09-12 10:53:18 the message was uploaded",
        "2026-09-12 10:53:19 the message was PROCESSED",
    ]


def test_scan_header_dir_sorts_hdr_files_and_ignores_other_files(tmp_path: Path):
    headers_dir = tmp_path / "headers"
    headers_dir.mkdir()
    (headers_dir / "b.hdr").write_text("unique-id=NXC-B\nsubject=b.txt\n", encoding="utf-8")
    (headers_dir / "a.hdr").write_text("unique-id=NXC-A\nsubject=a.txt\n", encoding="utf-8")
    (headers_dir / "note.txt").write_text("ignore me", encoding="utf-8")

    records = scan_header_dir(headers_dir, flow_type="received")

    assert [record.unique_id for record in records] == ["NXC-A", "NXC-B"]
    assert [record.flow_type for record in records] == ["received", "received"]

