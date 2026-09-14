# Sistema de Integracao FTP/SFTP e Mailbox Generix - Design MVP

Data: 2026-09-14

## Objetivo

Criar uma aplicacao Python executavel em consola, preparada para Windows Task Scheduler, que processe ficheiros por ciclos curtos. Em cada execucao, a aplicacao le a configuracao YAML, verifica transferencias pendentes, deteta ficheiros novos nas pastas configuradas, envia-os por FTP/SFTP, regista historico em SQLite e gera relatorios.

O MVP concentra-se no motor comum de transferencia generica. Os fluxos EDI Generix entram como perfis configuraveis sobre o mesmo motor, com documentacao inicial para mapear as pastas reais quando forem conhecidas.

## Escopo do MVP

Incluido:

- Execucao por comando `run-once`.
- Configuracao centralizada em YAML.
- Multiplas ligacoes ativas/inativas.
- Monitorizacao por polling durante a execucao.
- Verificacao de estabilidade antes do envio.
- Envio FTP e SFTP atraves de clientes com interface comum.
- Movimento local para `Enviados` em sucesso e `Erros` em falha.
- Historico em SQLite.
- Confirmacao remota por desaparecimento do ficheiro na pasta de destino.
- Timeout de confirmacao configuravel.
- Relatorios CSV, Excel e JSON.
- Logs estruturados em JSON Lines.
- Documentacao de instalacao, configuracao e mapeamento Generix.

Fora do MVP inicial:

- Servico Windows nativo.
- Interface grafica.
- Base de dados SQL Server.
- Cofre externo de segredos.
- Decisoes automaticas com base no conteudo funcional dos ficheiros EDI.
- Integracao direta com APIs do ARTSOFT ou Generix, salvo se forem disponibilizadas depois.

## Arquitetura

A aplicacao tera uma entrada CLI e modulos internos pequenos:

- `src/app.py`: ponto de entrada da consola.
- `src/config/`: leitura e validacao do YAML.
- `src/core/`: descoberta, estabilidade, processamento e movimentacao de ficheiros.
- `src/transfers/`: clientes FTP/SFTP e interface comum.
- `src/storage/`: SQLite, repositorios e migracoes simples.
- `src/reports/`: exportacao CSV, Excel e JSON.
- `src/logging_setup.py`: logs estruturados.
- `src/notifications/`: estrutura preparada para email, desligada por defeito no MVP.
- `docs/`: guias de instalacao, configuracao e mapeamento Generix.

O fluxo principal sera:

1. Carregar `config.yaml`.
2. Abrir ou criar a base SQLite.
3. Para cada ligacao ativa, verificar confirmacoes pendentes.
4. Listar ficheiros locais que correspondem ao padrao configurado.
5. Ignorar ficheiros ainda instaveis.
6. Registar deteccao no historico.
7. Enviar por FTP/SFTP.
8. Mover o ficheiro para `Enviados` ou `Erros`.
9. Registar estado final do envio.
10. Gerar relatorios do ciclo e consolidado diario.

## Configuracao

O ficheiro principal sera `config.yaml`. Estrutura prevista:

```yaml
app:
  database_path: data/integration.db
  log_dir: logs
  report_dir: reports

defaults:
  stable_after_seconds: 30
  confirmation_timeout_minutes: 120

connections:
  - name: laboratorio_x
    enabled: true
    flow_type: generic
    protocol: sftp
    host: sftp.exemplo.pt
    port: 22
    username: utilizador
    password_env: LAB_X_SFTP_PASSWORD
    source_dir: "\\\\servidor\\partilha\\saida"
    remote_dir: "/inbound"
    file_pattern: "*.edi"
    sent_dir: "Enviados"
    error_dir: "Erros"
```

As passwords podem ser referenciadas por variaveis de ambiente. Para SFTP com chave privada, a configuracao suportara `private_key_path` e `private_key_passphrase_env`.

## Modelo de Dados

SQLite guardara o historico operacional em tabelas simples:

- `connections`: snapshot minimo dos nomes das ligacoes processadas.
- `file_events`: um registo por ficheiro/processamento.
- `transfer_attempts`: tentativas de envio, duracao, erro e resultado.
- `confirmation_checks`: verificacoes de processamento remoto.

Estados de ficheiro:

- `detected`
- `skipped_unstable`
- `sent`
- `failed`
- `confirmed`
- `confirmation_timeout`

Cada registo guardara timestamps UTC e tambem valores locais nos relatorios quando util.

## FTP/SFTP

Os protocolos terao uma interface comum:

- `connect()`
- `upload(local_path, remote_path)`
- `exists(remote_path)`
- `close()`

Bibliotecas previstas:

- FTP: biblioteca standard `ftplib`.
- SFTP: `paramiko`.

Falhas numa ligacao nao interrompem as restantes. Cada excecao sera registada com o nome da ligacao, ficheiro, operacao e mensagem de erro.

## Estabilidade e Movimento Local

Um ficheiro so sera elegivel se:

- corresponder ao padrao configurado;
- nao estiver dentro das subpastas `Enviados` ou `Erros`;
- mantiver tamanho e data de modificacao durante o periodo `stable_after_seconds`.

Depois do envio:

- sucesso: mover para subpasta local `Enviados`;
- falha: mover para subpasta local `Erros`;
- conflitos de nome: acrescentar timestamp ao ficheiro movido.

## Confirmacao Remota

No MVP, a confirmacao usa a regra mais comum: se o ficheiro enviado ja nao existir na pasta remota, assume-se que foi recolhido/processado pelo destino.

Para cada ficheiro com estado `sent`, a execucao seguinte verifica:

- se ainda existe remotamente, mantem pendente;
- se desapareceu, marca `confirmed`;
- se excedeu `confirmation_timeout_minutes`, marca `confirmation_timeout`.

Esta regra sera configuravel por ligacao para permitir desligar confirmacao quando nao fizer sentido.

## Relatorios

Serao gerados:

- relatorio por execucao;
- relatorio diario consolidado;
- export CSV;
- export Excel `.xlsx`;
- export JSON estruturado.

Campos principais:

- nome da ligacao;
- tipo de fluxo;
- nome do ficheiro;
- origem local;
- destino remoto;
- data/hora de deteccao;
- inicio e fim do envio;
- duracao;
- estado do envio;
- estado da confirmacao;
- data/hora da confirmacao;
- mensagem de erro, quando existir.

## Generix e EDI

No MVP, Generix sera preparado como configuracao e documentacao, nao como integracao fechada. A estrutura real da mailbox ainda tem de ser mapeada.

Fluxos previstos:

- `generix_pharmacy_to_artsoft`: ficheiros recebidos das farmacias pela mailbox e importados pelo ARTSOFT.
- `generix_artsoft_to_lab`: ficheiros gerados pelo ARTSOFT e processados pela mailbox para laboratorios.

O documento `docs/generix-mailbox-mapping.md` guardara:

- pastas de entrada, saida, processamento, erro e arquivo;
- nomenclaturas observadas;
- formato dos ficheiros;
- indicadores de sucesso/erro existentes na mailbox;
- regras especificas por laboratorio ou farmacia.

## Operacao no Windows

O comando esperado sera semelhante a:

```powershell
python -m src.app run-once --config config.yaml
```

No Task Scheduler, a tarefa devera correr em intervalo definido pelo operador, por exemplo a cada 1 ou 5 minutos. A aplicacao deve terminar com codigo `0` quando o ciclo global foi executado, mesmo que uma ligacao individual falhe; falhas individuais ficam refletidas nos logs, base de dados e relatorios.

## Testes

Testes iniciais:

- validacao de configuracao YAML;
- deteccao e filtragem de ficheiros;
- verificacao de estabilidade;
- movimento para `Enviados` e `Erros`;
- persistencia SQLite;
- geracao de relatorios;
- clientes FTP/SFTP testados por mocks/fakes no MVP.

Testes manuais documentados:

- criar ficheiro de exemplo;
- executar `run-once`;
- confirmar movimento local;
- confirmar registo SQLite;
- confirmar relatorio;
- simular desaparecimento remoto e confirmar estado `confirmed`.

## Criterios de Aceitacao

O MVP esta aceite quando:

- uma ou mais ligacoes podem ser definidas no YAML sem alterar codigo;
- a execucao `run-once` processa todas as ligacoes ativas;
- ficheiros incompletos nao sao enviados;
- ficheiros enviados com sucesso sao movidos para `Enviados`;
- falhas sao isoladas por ligacao e movidas para `Erros`;
- historico operacional fica em SQLite;
- relatorios CSV, Excel e JSON sao gerados;
- confirmacoes remotas pendentes sao verificadas em execucoes seguintes;
- existe documentacao suficiente para instalar, configurar e agendar no Windows.

