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
- `edi_duplicate_key`
- `edi_duplicate_status`

Se o ficheiro ja tiver sido movido, o relatorio tenta ler o ficheiro em `Enviados` quando o estado e `sent` ou `confirmed`, em `Erros` quando o estado e `failed`, ou em `Duplicados` quando o estado e `duplicate`.

## Controlo de Duplicados

A Fase 1 do controlo de duplicados marca o relatorio sem bloquear envios.

A chave usada e:

```text
edi_remetente_gln|edi_fornecedor_gln|edi_serie_encomenda|edi_numero_encomenda
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
