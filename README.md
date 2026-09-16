# Relatorios Encomendas EDI EF

Aplicacao Python para integrar ficheiros por FTP/SFTP e preparar os fluxos EDI Generix de farmacias, ARTSOFT e laboratorios.

## Execucao Rapida

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .[dev]
copy config.example.yaml config.yaml
python -m integration_app.app run-once --config config.yaml
```

## Relatorio Generix Local

Para analisar os cabecalhos `.hdr` da mailbox Generix sem enviar ficheiros:

```powershell
$env:PYTHONPATH='src'
python -m integration_app.app generix-report --storage-root "C:\Users\TI\Documents\Influe-Generix\Bat\storage\cpip_20122611437260" --report-dir reports
```

O comando gera CSV e JSON com `unique-id`, assunto, origem, destino, estado `processed`, excepcoes operacionais, caminho do corpo, eventos do bloco `[log]` e resumo do EDI associado (`CAB`, quantidade de linhas `DET`, existencia de `TOT`, codigos GLN e nome de origem quando detectavel).
Tambem gera ficheiros `-exceptions.csv` e `-exceptions.json` apenas com registos sinalizados, e imprime no terminal os totais `Total`, `OK`, `Warnings` e `Errors`.
O ficheiro Excel `.xlsx` inclui as folhas `Todas`, `Excepcoes` e `Resumo`, com filtros e realce visual dos avisos/erros.

## API Local de Monitorizacao

Para consultar eventos, resumos, fornecedores e relatorios por HTTP local:

```powershell
python -m integration_app.api --db data/integration.db --reports reports
```

Depois de arrancar, abrir o dashboard no browser:

```text
http://127.0.0.1:8000/
```

O dashboard mostra resumo operacional, eventos recentes, fornecedores e relatorios gerados.

Na seccao `Configuracao`, permite activar/desactivar ligacoes existentes. Antes de alterar `config.yaml`, a aplicacao cria backup em `config.backups/`, valida a configuracao resultante e rejeita campos sensiveis como passwords, host, username, port e protocolo.

Para criar novas ligacoes a partir do dashboard, arrancar a API com a variavel `INTEGRATION_ADMIN_PASSWORD` definida. Essa password e pedida no formulario apenas para confirmar a operacao de administrador; nao e gravada no `config.yaml`.

Endpoints principais:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/summary`
- `http://127.0.0.1:8000/events`
- `http://127.0.0.1:8000/suppliers`
- `http://127.0.0.1:8000/reports`
- `PATCH http://127.0.0.1:8000/config/connections/{nome}`

## Execucao Diaria

Para executar envio e relatorio Generix no mesmo ciclo:

```powershell
powershell.exe -ExecutionPolicy Bypass -File "C:\Users\TI\Desktop\RelatoriosEncomendasEDI_EF\scripts\run-daily.ps1"
```

Por defeito, o script mantem relatorios e logs dos ultimos 30 dias. A retencao pode ser alterada com `-RetentionDays 60` ou desligada com `-DisableCleanup`.

## Campos no Relatorio de Envios

Os relatorios `run-*` tambem analisam ficheiros `Pedido_EDI_*.txt` quando ainda existem na pasta original, em `Enviados` ou em `Erros`. O relatorio extrai tipo de mensagem, nome/GLN do remetente, nome/GLN do fornecedor, serie, numero da encomenda, referencia interna como `TER/F200/202600525`, numero de linhas de encomenda iniciadas por `D` e controlo de duplicados por chave EDI.

Tambem sao suportadas encomendas XML `EOrders/EOrder`, incluindo os ficheiros Beiersdorf com `SellerVAT` `PT500043531`. Para estes XML, o relatorio extrai comprador, fornecedor, tipo, numero/data da encomenda, canal, numero de linhas `BuyOrderItem` e controlo de duplicados por chave XML.

Para bloquear operacionalmente duplicados sem parar a execucao, configurar na ligacao:

```yaml
duplicate_policy: move_to_duplicates
```

Neste modo, encomendas repetidas sao movidas para `Duplicados` e nao sao enviadas.

## Componentes

- Configuracao em YAML.
- Execucao `run-once` para Windows Task Scheduler.
- Historico SQLite.
- Relatorios CSV, Excel e JSON.
- Logs JSON Lines.
- Clientes FTP e SFTP.

## Documentacao

- Design: `docs/superpowers/specs/2026-09-14-integracao-ftp-sftp-generix-mvp-design.md`
- Plano: `docs/superpowers/plans/2026-09-14-integracao-ftp-sftp-generix-mvp-implementation.md`
- Generix: `docs/generix-mailbox-mapping.md`
- Campos EDI: `docs/order-edi-report-fields.md`
- Windows Task Scheduler: `docs/install-windows-task-scheduler.md`
