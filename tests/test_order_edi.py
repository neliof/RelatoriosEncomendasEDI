from pathlib import Path

from integration_app.order_edi import parse_order_edi_file


def test_parse_order_edi_file_extracts_filename_and_content_fields(tmp_path: Path):
    edi_path = tmp_path / "Pedido_EDI_Entregafarm_BAYER_F200-202600525.txt"
    edi_path.write_text(
        """HPEDIDO0001               PT5106785059125042
C   PT500043256                                                                                                                    2026072400010050         0001                                                                                          TER/F200/202600525
D0000015273289             20260724
D0000023045580             20260724
""",
        encoding="utf-8",
    )

    record = parse_order_edi_file(edi_path)

    assert record.tipo_mensagem == "HPEDIDO0001"
    assert record.remetente_nome == "Entregafarm"
    assert record.remetente_gln == "PT5106785059125042"
    assert record.fornecedor_nome == "BAYER"
    assert record.fornecedor_gln == "PT500043256"
    assert record.serie_encomenda == "F200"
    assert record.numero_encomenda == "202600525"
    assert record.numero_encomenda_conteudo == "TER/F200/202600525"
    assert record.linhas_encomenda == 2


def test_parse_order_edi_file_leaves_missing_fields_empty(tmp_path: Path):
    edi_path = tmp_path / "outro.txt"
    edi_path.write_text("HPEDIDO0001\n", encoding="utf-8")

    record = parse_order_edi_file(edi_path)

    assert record.remetente_nome is None
    assert record.fornecedor_nome is None
    assert record.fornecedor_gln is None
    assert record.numero_encomenda_conteudo is None
    assert record.linhas_encomenda == 0
