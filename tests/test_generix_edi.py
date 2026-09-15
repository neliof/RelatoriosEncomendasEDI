from pathlib import Path

from integration_app.generix.edi import parse_edi_file


def test_parse_edi_file_extracts_cab_summary_and_counts_details(tmp_path: Path):
    edi_path = tmp_path / "order.txt"
    edi_path.write_text(
        """CAB76329/275062/00                    9  80E202608030851                        PT5087356961990095                 PT5106785059125042                 Farmacia do Faial                  Estrada Regional 101 n. 63                                            Faial                              9230-053                EUR
DET0000105664032                            5664032
DSL1   100.00
DET0000205450838                            5450838
TOT00000000002
""",
        encoding="utf-8",
    )

    record = parse_edi_file(edi_path)

    assert record.path == edi_path
    assert record.cab_line.startswith("CAB76329")
    assert record.detail_count == 2
    assert record.has_total is True
    assert record.gln_codes == ["PT5087356961990095", "PT5106785059125042"]
    assert record.origin_name == "Farmacia do Faial"


def test_parse_edi_file_handles_missing_cab(tmp_path: Path):
    edi_path = tmp_path / "empty.txt"
    edi_path.write_text("DET0000105664032\n", encoding="utf-8")

    record = parse_edi_file(edi_path)

    assert record.cab_line is None
    assert record.detail_count == 1
    assert record.origin_name is None


def test_parse_edi_file_reads_windows_encoded_edi(tmp_path: Path):
    edi_path = tmp_path / "ansi.txt"
    edi_path.write_bytes(
        "CAB220 202600552                          EntregaFarm- Logística Farmacêutica\nDET000001\n".encode(
            "cp1252"
        )
    )

    record = parse_edi_file(edi_path)

    assert record.origin_name == "EntregaFarm- Logística Farmacêutica"
