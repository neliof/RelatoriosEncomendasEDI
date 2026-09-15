import csv
import json
from pathlib import Path

from integration_app.generix.reports import export_header_report


def test_export_header_report_writes_csv_and_json(tmp_path: Path):
    root = tmp_path / "Generix" / "Bat" / "storage" / "cpip_1"
    received = root / "received" / "headers"
    sent = root / "sent" / "headers"
    sent_data = root / "sent" / "data"
    received.mkdir(parents=True)
    sent.mkdir(parents=True)
    sent_data.mkdir(parents=True)
    edi_path = sent_data / "tx.txt"
    edi_path.write_text(
        """CAB220 202600552                          PT5106785059125042                 PT5066985992794093                 EntregaFarm- Logística FarmacêuticaPT5106785059125042                 ALCOTRANS (M)
DET0000015852355                                                               DIOFLAV 1000 MG 30 COMP
DET0000025852363                                                               DIOFLAV 1000 MG 60 COMP
TOT00000000002
""",
        encoding="utf-8",
    )
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
        f"""body-path={edi_path}
date=Sat, 12 Sep 2026 10:53:17 +0100
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
    assert json_rows[1]["edi_path"] == str(edi_path)
    assert json_rows[1]["edi_detail_count"] == 2
    assert json_rows[1]["edi_has_total"] is True
    assert json_rows[1]["edi_origin_name"] == "EntregaFarm- Logística Farmacêutica"
    assert "PT5106785059125042" in json_rows[1]["edi_gln_codes"]
