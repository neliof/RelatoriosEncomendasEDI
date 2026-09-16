# Local Read-Only Dashboard Frontend Design

## Objetivo

Criar um dashboard web local para monitorizar os fluxos EDI/XML, usando a API local ja existente como fonte de dados.

O dashboard deve ajudar a verificar rapidamente se existem envios falhados, duplicados, pendentes de confirmacao, fornecedores com problemas e relatorios recentes, sem editar configuracoes nem expor informacao sensivel.

## Ambito

Incluido:

- Pagina web local servida pela API FastAPI.
- Consulta dos endpoints existentes `/summary`, `/events`, `/suppliers` e `/reports`.
- Cartoes de resumo operacional.
- Tabela de eventos recentes com filtros basicos.
- Tabela de fornecedores.
- Lista de relatorios gerados.
- Botao de actualizacao manual.
- Indicacao visual de erros de carregamento.
- Testes automatizados para a rota do dashboard e ficheiros estaticos.

Excluido nesta fase:

- Login/autenticacao.
- Edicao de `config.yaml`.
- Gestao de passwords ou ficheiros `secrets/`.
- Criacao, alteracao ou remocao de agendamentos.
- Arranque manual de envios pelo dashboard.
- Escrita na base de dados.
- Framework JavaScript com build step.

## Arquitectura

O frontend sera servido pela propria API local para manter a instalacao simples em Windows:

```text
src/integration_app/api/
  app.py
  static/
    dashboard.html
    dashboard.css
    dashboard.js
```

`app.py` monta os ficheiros estaticos e disponibiliza `GET /` como entrada do dashboard.

O JavaScript do dashboard chama a API por URLs relativas, por exemplo `/summary` e `/events`, para funcionar no mesmo host/porta onde a API esta a correr.

## Modelo De Execucao

O utilizador arranca a API como ja definido:

```powershell
python -m integration_app.api --db data/integration.db --reports reports
```

Depois abre:

```text
http://127.0.0.1:8000/
```

## Interface

Primeiro ecra:

- Cabecalho compacto com nome do sistema e estado da ultima actualizacao.
- Linha de metricas:
  - Total
  - Enviados
  - Confirmados
  - Pendentes
  - Duplicados
  - Falhados
- Filtros de eventos:
  - Estado
  - Ligacao
  - Limite de registos
- Tabela de eventos:
  - Data detectada
  - Ligacao
  - Protocolo
  - Estado
  - Confirmacao
  - Ficheiro local
  - Erro
- Secao de fornecedores:
  - Fornecedor
  - Total
  - Duplicados
  - Falhados
- Secao de relatorios:
  - Nome
  - Tipo
  - Tamanho
  - Modificado em

## Estilo Visual

O dashboard deve parecer uma ferramenta operacional:

- Layout denso mas legivel.
- Sem hero, marketing ou decoracao pesada.
- Paleta neutra com acentos por estado:
  - Verde para confirmado/sucesso.
  - Amarelo para pendente/duplicado.
  - Vermelho para falha.
  - Azul discreto para informacao.
- Tabelas com leitura facil, alturas consistentes e texto sem sobreposicao.
- Responsivo para portatil e ecras pequenos, com tabelas em scroll horizontal quando necessario.

## Estados E Erros

O dashboard deve mostrar:

- Estado "a carregar" enquanto consulta a API.
- Mensagem curta quando a API devolve erro.
- Mensagem curta quando nao existem dados.
- Hora local da ultima actualizacao bem sucedida.

Falhas de um endpoint nao devem impedir totalmente a pagina de abrir; cada bloco pode mostrar a sua propria mensagem de erro.

## Seguranca

Esta fase continua apenas local e read-only:

- Sem endpoints de escrita.
- Sem passwords.
- Sem conteudo bruto de `config.yaml`.
- Sem acesso a `secrets/`.
- Sem comandos operacionais de envio ou agendamento.

Se futuramente o dashboard for exposto na rede, sera necessario adicionar autenticacao e controlo de permissoes antes de qualquer funcionalidade administrativa.

## Testes

Cobrir:

- `GET /` devolve HTML do dashboard.
- Ficheiros estaticos principais existem e sao servidos.
- O HTML referencia o CSS e o JavaScript esperados.
- Os endpoints JSON existentes continuam a passar.

## Criterios De Aceitacao

- `python -m integration_app.api --db data/integration.db --reports reports` arranca a API local.
- `http://127.0.0.1:8000/` abre o dashboard.
- O dashboard carrega resumo, eventos, fornecedores e relatorios via API.
- A suite `pytest` passa.
- Nao ha alteracao ao envio FTP/SFTP.
- Nao ha alteracao ao Task Scheduler.
- Nao ha exposicao de passwords, secrets ou configuracao sensivel.
