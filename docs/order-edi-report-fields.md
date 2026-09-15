# Campos do Relatorio de Encomendas EDI/XML

## Fonte

Ficheiros enviados como:

```text
C:\Edi\Send\Enviados\Pedido_EDI_Entregafarm_BAYER_F200-202600525.txt
C:\Edi\Send\Enviados\Pedido_EDI_Imefar_5600000975855F002-202600143.XML
```

## Regras Observadas em TXT

- Nome do ficheiro: `Pedido_EDI_<Remetente>_<Fornecedor>_<Serie>-<Numero>.txt`.
- Primeira linha: primeiro campo e o tipo de mensagem; o primeiro GLN encontrado e o GLN do remetente.
- Segunda linha: primeiro GLN encontrado e o GLN do fornecedor; a referencia `TER/F200/202600525` identifica a encomenda no conteudo.
- Linhas iniciadas por `D`: linhas da encomenda.

## Regras Observadas em XML

- Raiz: `EOrders`.
- Encomenda: `EOrder`.
- Numero completo da encomenda: `ByerOrderNumber`, por exemplo `F002/202600143`.
- Serie/tipo: `OrderType`.
- Data: `OrderDate`.
- Comprador: `BuyerVAT` e `BuyerEANCode`.
- Fornecedor: `SellerVAT`, `SellerEANCode` e `SellerCanal`.
- Para `SellerVAT` `PT500043531`, o nome do fornecedor e `BEIERSDORF PORTUGUESA, LDA.`.
- Linhas da encomenda: elementos `BuyOrderItem`.

## Campos Acrescentados aos Relatorios `run-*`

- `edi_tipo_mensagem`
- `edi_remetente_nome`
- `edi_remetente_gln`
- `edi_fornecedor_nome`
- `edi_fornecedor_gln`
- `edi_serie_encomenda`
- `edi_numero_encomenda`
- `edi_numero_encomenda_conteudo`
- `edi_linhas_encomenda`
- `edi_duplicate_key`
- `edi_duplicate_status`
- `xml_buyer_name`
- `xml_buyer_vat`
- `xml_buyer_ean`
- `xml_seller_vat`
- `xml_seller_name`
- `xml_seller_ean`
- `xml_seller_canal`
- `xml_order_type`
- `xml_order_number`
- `xml_buyer_order_number`
- `xml_order_date`
- `xml_linhas_encomenda`
- `xml_duplicate_key`
- `xml_duplicate_status`

Se o ficheiro ja tiver sido movido, o relatorio tenta ler o ficheiro em `Enviados` quando o estado e `sent` ou `confirmed`, em `Erros` quando o estado e `failed`, ou em `Duplicados` quando o estado e `duplicate`.

## Controlo de Duplicados

A Fase 1 do controlo de duplicados marca o relatorio sem bloquear envios.

A chave usada e:

```text
edi_remetente_gln|edi_fornecedor_gln|edi_serie_encomenda|edi_numero_encomenda
xml_buyer_ean|xml_seller_vat|xml_order_type|xml_order_number
```

Estados possiveis:

- `unique`: primeira ocorrencia encontrada no historico do relatorio;
- `duplicate`: ja existia uma ocorrencia anterior com a mesma chave;
- `unknown`: faltam campos para formar a chave.

A Fase 2 acrescenta controlo operacional configuravel por ligacao:

```yaml
duplicate_policy: report_only
```

Valores aceites:

- `report_only`: comportamento por defeito; envia normalmente e apenas marca duplicados no relatorio;
- `move_to_duplicates`: antes do upload, se ja existir no historico uma encomenda com a mesma chave, move o novo ficheiro para `Duplicados`, nao envia para FTP/SFTP e regista estado `duplicate`.

Para configurar uma ligacao separada para XML:

```yaml
file_pattern: "*.XML"
duplicate_policy: move_to_duplicates
```
