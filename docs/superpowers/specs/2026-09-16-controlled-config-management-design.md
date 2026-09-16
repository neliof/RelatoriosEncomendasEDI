# Controlled Config Management Design

## Objetivo

Permitir gerir parte da configuracao operacional a partir da API/dashboard local, com escrita controlada em `config.yaml`, backups automaticos e validacao antes de gravar.

Esta fase deve permitir operacoes pequenas e seguras, sem expor passwords e sem alterar directamente ficheiros sensiveis.

## Ambito

Incluido:

- Activar ou desactivar uma ligacao existente.
- Alterar campos operacionais simples de uma ligacao existente:
  - `source_dir`
  - `remote_dir`
  - `file_pattern`
  - `duplicate_policy`
  - `confirm_remote_processing`
- Criar backup automatico antes de gravar.
- Validar o ficheiro resultante com `load_config`.
- Escrita atomica: gravar temporario e substituir o ficheiro final apenas depois de validar.
- Endpoints API locais para leitura e actualizacao controlada.
- Accoes no dashboard para activar/desactivar ligacoes.
- Testes automatizados para backup, validacao e bloqueio de campos sensiveis.

Excluido nesta fase:

- Alterar passwords.
- Mostrar valores de `password_env`.
- Alterar `host`, `username`, `port`, `protocol` ou `private_key_path` pelo dashboard.
- Criar novas ligacoes.
- Apagar ligacoes.
- Testar ligacoes FTP/SFTP.
- Gerir Windows Task Scheduler.
- Expor a API fora de `127.0.0.1`.

## Modelo De Seguranca

A API continua local.

Antes de qualquer escrita:

- O nome da ligacao tem de existir.
- Apenas campos permitidos podem ser alterados.
- Campos sensiveis sao rejeitados:
  - `password_env`
  - `private_key_path`
  - `private_key_passphrase_env`
  - `username`
  - `host`
  - `port`
  - `protocol`
- O novo YAML e validado por `load_config`.
- Se a validacao falhar, o ficheiro original fica intacto.
- E criado backup em `config.backups/config-YYYYMMDD-HHMMSS.yaml`.

## Endpoints

### `PATCH /config/connections/{name}`

Actualiza campos permitidos de uma ligacao existente.

Pedido:

```json
{
  "enabled": false,
  "source_dir": "C:\\Edi\\Send",
  "remote_dir": "/FACT/Aurovitas/",
  "file_pattern": "*.txt",
  "duplicate_policy": "move_to_duplicates",
  "confirm_remote_processing": true
}
```

Resposta:

```json
{
  "connection_name": "primeira_ligacao_teste",
  "updated": true,
  "backup_path": "config.backups/config-20260916-120000.yaml"
}
```

Erros:

- `404` se a ligacao nao existir.
- `400` se o pedido tentar alterar campos proibidos.
- `400` se `duplicate_policy` for invalido.
- `400` se o YAML resultante nao passar em `load_config`.

## Dashboard

Na secao `Configuracao`:

- Mostrar estado activo/inactivo por ligacao.
- Botao para activar/desactivar cada ligacao.
- Depois da accao, recarregar `/config/summary`.
- Mostrar erro curto se a actualizacao falhar.

Nesta fase, os restantes campos podem ficar apenas visiveis; edicao detalhada pode vir depois.

## Arquitectura

Criar modulo dedicado:

```text
src/integration_app/api/config_management.py
```

Responsabilidades:

- carregar YAML com parser seguro;
- aplicar alteracoes permitidas;
- criar backup;
- validar com `load_config`;
- substituir `config.yaml` de forma atomica.

`app.py` deve apenas receber o pedido HTTP, chamar o modulo e devolver resposta JSON.

## Criterios De Aceitacao

- Activar/desactivar uma ligacao existente cria backup e actualiza `config.yaml`.
- Campos sensiveis sao rejeitados.
- Pedido para ligacao inexistente devolve `404`.
- Se a validacao falhar, `config.yaml` fica intacto.
- Dashboard consegue activar/desactivar ligacao e refrescar o resumo.
- A suite `pytest` passa.
