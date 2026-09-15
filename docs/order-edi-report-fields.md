# Campos do Relatorio de Encomendas EDI

## Fonte

Ficheiros enviados como:

```text
C:\Edi\Send\Enviados\Pedido_EDI_Entregafarm_BAYER_F200-202600525.txt
```

## Regras Observadas

- Nome do ficheiro: `Pedido_EDI_<Remetente>_<Fornecedor>_<Serie>-<Numero>.txt`.
- Primeira linha: primeiro campo e o tipo de mensagem; o primeiro GLN encontrado e o GLN do remetente.
- Segunda linha: primeiro GLN encontrado e o GLN do fornecedor; a referencia `TER/F200/202600525` identifica a encomenda no conteudo.
- Linhas iniciadas por `D`: linhas da encomenda.

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

Se o ficheiro ja tiver sido movido, o relatorio tenta ler o ficheiro em `Enviados` quando o estado e `sent`, ou em `Erros` quando o estado e `failed`.
