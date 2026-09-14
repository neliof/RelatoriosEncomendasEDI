import csv
import json
from pathlib import Path

from integration_app.generix.reports import export_header_report


def test_export_header_report_writes_csv_and_json(tmp_path: Path):
    root = tmp_path / "Generix" / "Bat" / "storage" / "cpip_1"
    received = root / "received" / "headers"
    sent = root / "sent" / "headers"
    received.mkdir(parents=True)
    sent.mkdir(parents=True)
    (received / "rx.hdr").write_text(
        """date=Fri, 04 Sep 2026 09:10:11 +0100
from=farmacia@netixone.com.pt
to=influe@netixone.com.pt
subject=ord5139292776.txt
unique-id=NXC-RX
[log]
2026-09-04 09:10:12 message received.
""",
        encoding="utf-8",
    )
    (sent / "tx.hdr").write_text(
        """date=Sat, 12 Sep 2026 10:53:17 +0100
from=influe@netixone.com.pt
to=fch@netixone.com.pt
subject=Encomenda_20260912_105317.txt
unique-id=NXC-TX
disposition=automatic-action/MDN-sent-automatically; processed
[log]
2026-09-12 10:53:19 the message was PROCESSED
""",
        encoding="utf-8",
    )

    written = export_header_report(root, tmp_path / "reports", run_id="generix-test")

    assert written == [tmp_path / "reports" / "generix-test.csv", tmp_path / "reports" / "generix-test.json"]
    with written[0].open("r", newline="", encoding="utf-8") as handle:
        csv_rows = list(csv.DictReader(handle))
    json_rows = json.loads(written[1].read_text(encoding="utf-8"))
    assert [row["flow_type"] for row in csv_rows] == ["received", "sent"]
    assert json_rows[1]["unique_id"] == "NXC-TX"
    assert json_rows[1]["processed"] is True

