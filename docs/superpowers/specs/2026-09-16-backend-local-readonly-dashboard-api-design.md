# Backend Local Read-Only Dashboard API Design

## Objetivo

Criar uma API local, apenas de leitura, para consultar o estado operacional da integração EDI/XML sem alterar ligações FTP/SFTP, passwords, ficheiros de configuração ou agendamentos.

Esta API será a base para um futuro dashboard web. Nesta fase, o foco é expor dados fiáveis da base SQLite e da pasta `reports/`.

## Âmbito

Incluído:

- API local em Python.
- Consulta da base `data/integration.db`.
- Consulta da pasta `reports/`.
- Endpoints JSON para estado, resumo, eventos, fornecedores e relatórios.
- Documentação de arranque local.
- Testes automatizados dos endpoints.

Excluído nesta fase:

- Frontend web.
- Autenticação.
- Edição de `config.yaml`.
- Gestão de passwords.
- Gestão de Task Scheduler.
- Execução manual de envios por API.
- Escrita na base de dados.

## Tecnologia

- Python 3.11+.
- FastAPI para a API HTTP.
- Uvicorn para servidor local.
- SQLite existente como fonte de dados.
- `pytest` para testes.
- `fastapi.testclient.TestClient` para testes de endpoints.

Dependências novas:

- `fastapi`.
- `uvicorn`.

## Modelo De Execução

A API corre localmente, apontando para uma base SQLite e para uma pasta de relatórios:

```powershell
python -m integration_app.api --db data/integration.db --reports reports
```

Por defeito:

- `--db`: `data/integration.db`
- `--reports`: `reports`
- host: `127.0.0.1`
- port: `8000`

## Endpoints

### `GET /health`

Confirma que a API está viva e que a base existe.

Resposta:

```json
{
  "status": "ok",
  "database_exists": true
}
```

### `GET /summary`

Devolve totais agregados dos eventos registados.

Campos:

- `total_files`
- `sent_count`
- `confirmed_count`
- `duplicate_count`
- `failed_count`
- `pending_count`
- `unknown_count`
- `last_detected_at`

Notas:

- `sent_count` inclui estados `sent` e `confirmed`.
- `pending_count` usa `confirmation_status == "pending"`.
- estados desconhecidos contam em `unknown_count`.

### `GET /events`

Lista eventos de envio, ordenados do mais recente para o mais antigo.

Filtros opcionais:

- `status`
- `connection_name`
- `date_from`
- `date_to`
- `limit`

`date_from` e `date_to` usam formato `YYYY-MM-DD` e aplicam-se a `detected_at`.

Resposta:

```json
{
  "items": [
    {
      "connection_name": "beiersdorf_xml",
      "flow_type": "generic",
      "protocol": "ftp",
      "local_path": "C:\\Edi\\Send\\ficheiro.XML",
      "remote_path": "/FACT/Aurovitas/ficheiro.XML",
      "status": "confirmed",
      "detected_at": "2026-09-15T10:00:00+00:00",
      "sent_at": "2026-09-15T10:00:01+00:00",
      "confirmation_status": "confirmed",
      "confirmation_checked_at": "2026-09-15T10:10:00+00:00",
      "error_message": null
    }
  ]
}
```

### `GET /suppliers`

Lista fornecedores detectados a partir dos relatórios enriquecidos.

Fonte:

- campos EDI/XML gerados por `export_reports`;
- para evitar duplicar parsing, esta fase pode calcular fornecedores a partir das linhas enriquecidas existentes no exportador.

Resposta:

```json
{
  "items": [
    {
      "supplier_name": "BAYER",
      "total_files": 9,
      "failed_count": 0,
      "duplicate_count": 2
    }
  ]
}
```

### `GET /reports`

Lista ficheiros existentes em `reports/`.

Campos:

- `name`
- `path`
- `kind`
- `size_bytes`
- `modified_at`

`kind` deriva do nome:

- `summary`
- `generix`
- `generix_exceptions`
- `run`
- `other`

## Arquitectura

Criar um pacote dedicado:

```text
src/integration_app/api/
  __init__.py
  __main__.py
  app.py
  read_models.py
```

Responsabilidades:

- `app.py`: cria a aplicação FastAPI e define endpoints.
- `read_models.py`: funções puras de leitura/agregação sobre SQLite e `reports/`.
- `__main__.py`: CLI local para arrancar Uvicorn.

A API não deve depender de passwords nem de clientes FTP/SFTP.

## Segurança

Nesta fase a API é local:

- host por defeito `127.0.0.1`;
- sem escrita;
- sem endpoints administrativos;
- sem exposição de passwords, secrets ou conteúdo de `config.yaml`.

Se no futuro for exposta na rede, será obrigatório acrescentar autenticação e permissões antes de qualquer endpoint administrativo.

## Testes

Cobrir:

- `/health` responde quando a base existe.
- `/summary` calcula contagens correctamente.
- `/events` aplica filtros básicos.
- `/reports` lista ficheiros e classifica `summary`, `generix`, `run`.
- leitura é só leitura: testes não devem alterar `file_events`.

## Critérios De Aceitação

- A API arranca localmente com `python -m integration_app.api`.
- `GET /health`, `/summary`, `/events`, `/suppliers` e `/reports` devolvem JSON.
- A suite `pytest` passa.
- Não há alteração ao envio FTP/SFTP.
- Não há alteração ao Task Scheduler.
- Não há exposição de passwords ou ficheiros `secrets/`.
