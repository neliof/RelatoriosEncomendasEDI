from pathlib import Path

from integration_app.order_xml import order_xml_duplicate_key, parse_order_xml_file


def test_parse_order_xml_file_extracts_beiersdorf_order_fields(tmp_path: Path):
    xml_path = tmp_path / "Pedido_EDI_Imefar_5600000975855F002-202600143.XML"
    xml_path.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<EOrders>
  <EOrder>
    <ByerOrderNumber>F002/202600143</ByerOrderNumber>
    <OrderDate>2026-09-14</OrderDate>
    <OrderType>F002</OrderType>
    <BuyerVAT>511000685</BuyerVAT>
    <BuyerEANCode>5600000975855</BuyerEANCode>
    <SellerVAT>PT500043531</SellerVAT>
    <SellerEANCode>5600000975855</SellerEANCode>
    <SellerCanal>Mass Market</SellerCanal>
    <BuyOrderItem>
      <ItemLineNumber>1</ItemLineNumber>
      <ProductIdentifier>4005808801046</ProductIdentifier>
      <Quantity>240.00</Quantity>
      <Bonus>0.00</Bonus>
    </BuyOrderItem>
    <BuyOrderItem>
      <ItemLineNumber>2</ItemLineNumber>
      <ProductIdentifier>4005900297035</ProductIdentifier>
      <Quantity>12.00</Quantity>
      <Bonus>0.00</Bonus>
    </BuyOrderItem>
  </EOrder>
</EOrders>
""",
        encoding="utf-8",
    )

    record = parse_order_xml_file(xml_path)

    assert record.buyer_name == "Imefar"
    assert record.buyer_vat == "511000685"
    assert record.buyer_ean == "5600000975855"
    assert record.seller_vat == "PT500043531"
    assert record.seller_name == "BEIERSDORF PORTUGUESA, LDA."
    assert record.seller_ean == "5600000975855"
    assert record.seller_canal == "Mass Market"
    assert record.order_type == "F002"
    assert record.order_number == "202600143"
    assert record.buyer_order_number == "F002/202600143"
    assert record.order_date == "2026-09-14"
    assert record.linhas_encomenda == 2
    assert order_xml_duplicate_key(record) == "5600000975855|PT500043531|F002|202600143"


def test_parse_order_xml_file_leaves_missing_fields_empty(tmp_path: Path):
    xml_path = tmp_path / "manual.xml"
    xml_path.write_text("<EOrders><EOrder /></EOrders>", encoding="utf-8")

    record = parse_order_xml_file(xml_path)

    assert record.buyer_name is None
    assert record.seller_name is None
    assert record.order_number is None
    assert record.linhas_encomenda == 0
    assert order_xml_duplicate_key(record) is None
