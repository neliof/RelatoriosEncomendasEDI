# Mapeamento Mailbox Generix

## Objetivo

Registar a estrutura real de pastas e indicadores da mailbox Generix antes de activar regras especificas de EDI.

## Fonte Observada

Este mapeamento inicial foi feito a partir da copia local:

```text
C:\Users\TI\Documents\Influe-Generix
```

A primeira inspecao foi limitada a nomes de pastas, nomes de ficheiros, extensoes, tamanhos e datas. Depois foi aberta uma amostra pequena de `received\data`, `sent\data`, `sent\headers` e `sent\receipts` para confirmar metadados e indicadores de processamento.

## Estrutura Principal

| Pasta | Papel provavel | Observacoes |
| --- | --- | --- |
| `Bat` | Instalacao/utilitarios NetIXOne/Generix | Contem executaveis, ficheiro `.bat`, configuracao, logs e storage. |
| `Bat\config` | Configuracao nativa NetIXOne | Contem ficheiros `.nxc`: `crypto`, `locprof`, `pipe`, `protocol`, `remprof`, `transport`. |
| `Bat\Log` | Logs nativos da mailbox | Contem logs diarios `YYYYMMDD_NXC.log`. |
| `Bat\Empty` | Encomendas vazias/sem conteudo | Contem varios `Encomenda_YYYYMMDD_HHMMSS.txt` com tamanho 0. |
| `Bat\storage\cpip_20122611437260` | Storage da mailbox | Tem subpastas `received` e `sent`. |
| `Disks\config` | Configuracao adicional | Ainda por confirmar. |
| `Netixone\In` | Entrada operacional NetIXOne | Pasta encontrada vazia na copia analisada. |
| `Netixone\Out` | Saida operacional NetIXOne | Contem apenas subpasta `.lacie` na copia analisada. |
| `Netixone\Documentos Fase Testes` | Amostras historicas/teste | Contem exemplos de encomendas, respostas e casos de cliente inexistente. |

## Storage Received

Base:

```text
C:\Users\TI\Documents\Influe-Generix\Bat\storage\cpip_20122611437260\received
```

| Subpasta | Conteudo observado | Quantidade | Papel provavel |
| --- | --- | ---: | --- |
| `received\data` | `NXC-*.txt` | 30 | Dados/mensagens recebidas pela mailbox. |
| `received\headers` | `*.hdr` | 30 | Cabecalhos/metadados das mensagens recebidas. |
| `received\messages` | sem ficheiros observados | 0 | Mensagens completas ou staging, por confirmar. |
| `received\trash` | sem ficheiros observados | 0 | Lixo/descartados, por confirmar. |
| `received` | `*.rcv` | 1 | Possivel indice/estado da area de recebidos. |

Exemplos de ficheiros recebidos em `received\data`:

```text
NXC-1785745080-655-0.txt
NXC-1785745081-446-1.txt
NXC-1788244144-230-6.txt
```

Formato observado em `received\data`:

- primeira linha `CAB...`;
- linhas de detalhe `DET...`;
- linhas de desconto/resumo `DSL...`, quando aplicavel;
- linha final `TOT...`;
- a amostra inclui identificacao da farmacia no registo `CAB`.

Campos uteis observados em `received\headers\*.hdr`:

- `body-path`: caminho para o ficheiro em `received\data`;
- `date`: data/hora da mensagem;
- `from` e `to`: caixas NetIXOne envolvidas;
- `message-id`;
- `receipt=ON`;
- `subject`: nome original da mensagem, por exemplo `ord*.txt`;
- `unique-id`: identificador `NXC-*`;
- bloco `[log]` com evento `message received`.

## Storage Sent

Base:

```text
C:\Users\TI\Documents\Influe-Generix\Bat\storage\cpip_20122611437260\sent
```

| Subpasta | Conteudo observado | Quantidade | Papel provavel |
| --- | --- | ---: | --- |
| `sent\data` | `*.txt` | 150 | Dados/mensagens enviadas pela mailbox. |
| `sent\headers` | `*.hdr` | 150 | Cabecalhos/metadados das mensagens enviadas. |
| `sent\messages` | `*.eml` | 150 | Mensagens enviadas em formato email/mensagem. |
| `sent\receipts` | `*.eml` | 150 | Recibos/confirmacoes de envio ou processamento. |
| `sent\trash` | sem ficheiros observados | 0 | Lixo/descartados, por confirmar. |
| `sent` | `*.snd` | 1 | Possivel indice/estado da area de enviados. |

Formato observado em `sent\data`:

- primeira linha `CAB...`;
- linhas de detalhe `DET...`;
- conteudo com referencias de encomenda, produtos, quantidades, precos e totalizadores;
- a amostra inclui entidade emissora EntregaFarm e indicios de laboratorio/destino no registo `CAB`.

Campos uteis observados em `sent\headers\*.hdr`:

- `body-path`: caminho para o ficheiro em `sent\data`;
- `date`: data/hora da mensagem enviada;
- `disposition=automatic-action/MDN-sent-automatically; processed`;
- `message-id`;
- `pipe-id`;
- `receipt=ON`;
- `subject`: nome original, por exemplo `Encomenda_YYYYMMDD_HHMMSS.txt`;
- `unique-id`: identificador `NXC-*`;
- bloco `[log]` com eventos `the message was uploaded`, `processing a receipt` e `the message was PROCESSED`.

Formato observado em `sent\receipts\*.eml`:

- mensagem MIME `multipart/report`;
- assunto `Message Disposition Notification`;
- texto a indicar que a mensagem foi recebida e que o processamento EDI foi iniciado;
- bloco `message/disposition-notification`;
- `Original-Message-ID`;
- `Disposition: automatic-action/MDN-sent-automatically; processed`.

## Farmacias para ARTSOFT

| Elemento | Valor observado |
| --- | --- |
| Pasta onde a mailbox deixa ficheiros recebidos | `Bat\storage\cpip_20122611437260\received\data` |
| Padrao de ficheiro | `NXC-*.txt` |
| Pasta de cabecalhos/metadados | `Bat\storage\cpip_20122611437260\received\headers` com `*.hdr` |
| Pasta de ficheiros importados pelo ARTSOFT | Nao identificada na copia. |
| Pasta de erros | Nao identificada na copia. Candidato a investigar: logs em `Bat\Log`. |
| Indicador de recepcao pela mailbox | `received\headers\*.hdr` com `[log] ... message received`. |
| Indicador de sucesso | Nao confirmado para importacao ARTSOFT. A recepcao Generix esta confirmada no `.hdr`, mas falta confirmar o evento de importacao no ERP. |
| Indicador de erro | Nao confirmado. Investigar `Bat\Log` e casos em `Netixone\Documentos Fase Testes\Cliente nao existe`. |

## ARTSOFT para Laboratorios

| Elemento | Valor observado |
| --- | --- |
| Pasta onde o ARTSOFT gera encomendas | Candidato: `Netixone\In`; estava vazia na copia analisada. |
| Padrao de ficheiro | Exemplos historicos: `Encomenda_*.txt`, `ord*.txt`. |
| Pasta recolhida pela mailbox | Candidato: `Netixone\In`; por confirmar. |
| Pasta de enviados/confirmados | `Bat\storage\cpip_20122611437260\sent\data`, `sent\messages`, `sent\receipts`. |
| Pasta de erros | Nao identificada claramente. Candidatos: `Bat\Empty`, `Bat\Log`, `Netixone\Documentos Fase Testes\Cliente nao existe`. |
| Indicador de upload pela mailbox | `sent\headers\*.hdr` com `[log] ... the message was uploaded`. |
| Indicador de processamento | `sent\headers\*.hdr` com `the message was PROCESSED` e/ou `sent\receipts\*.eml` com `Disposition: ... processed`. |
| Indicador de envio ao laboratorio | Candidato forte confirmado: recibo em `sent\receipts\*.eml` ligado ao `Original-Message-ID`. Falta confirmar se isto equivale a entrega final ao laboratorio ou apenas processamento pela plataforma NetIXOne. |

## Amostras de Teste Observadas

Base:

```text
C:\Users\TI\Documents\Influe-Generix\Netixone\Documentos Fase Testes
```

| Padrao | Papel provavel |
| --- | --- |
| `Encomenda_YYYYMMDD_HHMMSS.txt` | Encomendas geradas para teste. |
| `ord*.txt` | Encomendas em formato alternativo/historico. |
| `RespTransfOrder_YYYYMMDD_HHMMSS.txt` | Respostas de transferencia de encomenda. |
| `Cliente nao existe\*.txt` e `*.BCK` | Casos de erro/cliente inexistente. |

## Regras por Entidade

| Entidade | Tipo | Padrao | Pasta | Observacoes |
| --- | --- | --- | --- | --- |
| Generix/NetIXOne | Mailbox | `NXC-*.txt` + `*.hdr` | `Bat\storage\cpip_20122611437260\received` | Fluxo recebido, provavelmente Farmacias para ARTSOFT. |
| Generix/NetIXOne | Mailbox | `*.txt`, `*.hdr`, `*.eml` | `Bat\storage\cpip_20122611437260\sent` | Fluxo enviado, provavelmente ARTSOFT para Laboratorios. |
| ARTSOFT/Laboratorios | Encomendas | `Encomenda_*.txt`, `ord*.txt` | `Netixone\In` ou area de testes | Pasta operacional ainda por confirmar. |
| Erros de cliente | Erro | `ord*.txt`, `*.BCK` | `Netixone\Documentos Fase Testes\Cliente nao existe` | Usar como referencia para regras de erro, nao como pasta operacional. |

## Questoes Pendentes

1. Confirmar se `Netixone\In` e a pasta real onde o ARTSOFT deposita encomendas para laboratorios.
2. Confirmar se `Netixone\Out` e usado pela mailbox ou se e apenas uma pasta historica/auxiliar.
3. Analisar uma amostra segura de `received\data\NXC-*.txt` para identificar farmacia de origem.
4. Analisar uma amostra segura de `sent\data\*.txt` para identificar laboratorio de destino.
5. Confirmar com a operacao se `sent\receipts\*.eml` com `Disposition: ... processed` representa entrega final ao laboratorio ou apenas processamento pela mailbox.
6. Analisar um log recente `Bat\Log\YYYYMMDD_NXC.log` para extrair eventos de sucesso/erro e correlacionar com `unique-id`/`message-id`.
