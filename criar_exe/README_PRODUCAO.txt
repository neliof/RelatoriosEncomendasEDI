RELATORIOS ENCOMENDAS EDI - INSTALACAO DE PRODUCAO
==================================================

Esta pasta contem a distribuicao executavel de producao.

CONTEUDO
--------
- RelatoriosEncomendasEDI.exe    Servidor FastAPI + Dashboard
- nssm.exe                       Gestor de servicos Windows
- install_service.bat            Instala como Windows Service (admin)
- uninstall_service.bat          Desinstala o servico (admin)
- _internal/                     Dependencias Python/bibliotecas
- data/                          Banco de dados SQLite (integration.db)
- logs/                          Registos da aplicacao
- reports/                       Relatorios gerados
- config.example.yaml            Exemplo de configuracao

INSTALACAO RAPIDA
-----------------

1. Copiar esta pasta para um local permanente, ex:
   C:\Program Files\RelatoriosEncomendasEDI

2. Abrir Command Prompt/PowerShell como Administrador

3. Navegar ate a pasta:
   cd "C:\Program Files\RelatoriosEncomendasEDI"

4. Executar instalacao do servico:
   install_service.bat

5. Aguardar conclusao. O dashboard estara disponivel em:
   http://127.0.0.1:8000

PRIMEIRO ACESSO
---------------

1. Abrir http://127.0.0.1:8000 num navegador

2. Na aba "Configuracao" > "Configuracoes Gerais":
   - Definir localizacao Generix Mailbox (se aplicavel)
   - Adicionar ligacoes FTP/SFTP conforme necessario

3. Em "Nova Ligacao":
   - Nome: identificador unico (ex: "FTP_Fornecedor_A")
   - Protocolo: FTP, SFTP ou Local
   - Tipo: Receber ou Enviar
   - Preencher dados de conexao

4. Em "Agendar Ligacao":
   - Ativar agendamento
   - Escolher frequencia (diaria, hora em hora, etc.)

FUNCIONAMENTO COMO SERVICO
---------------------------

Apos instalacao:
- O servico inicia automaticamente na boot do Windows
- Dashboard acessivel 24/7 em http://127.0.0.1:8000
- Processamento automatico conforme agendamento definido
- Registos em: logs/service.log e logs/service_error.log

Para parar o servico:
  nssm stop RelatoriosEncomendasEDI

Para reiniciar:
  nssm restart RelatoriosEncomendasEDI

Para ver status:
  nssm status RelatoriosEncomendasEDI

DESINSTALACAO
-------------

Executar como Administrador:
  uninstall_service.bat

Os dados em "data/" nao sao removidos. Para eliminar, apague a pasta
manualmente apos desinstalacao.

BACKUP E RECUPERACAO
--------------------

Dados persistentes:
  data/integration.db         Base de dados
  logs/                       Registos tecnico

Antes de atualizar, copie:
  data/integration.db

Em caso de erro critico:
  1. Parar servico: nssm stop RelatoriosEncomendasEDI
  2. Restaurar copia: copiar integration.db para data/
  3. Reiniciar servico: nssm start RelatoriosEncomendasEDI

CONFIGURACAO AVANCADA
---------------------

Variavel de ambiente INTEGRATION_ADMIN_PASSWORD:
  Requerida para criar/editar/eliminar ligacoes via dashboard.

  set INTEGRATION_ADMIN_PASSWORD=sua_senha_admin

Diretorio de dados alternativo:
  Editar RelatoriosEncomendasEDI.exe (via NSSM) com:
  nssm set RelatoriosEncomendasEDI AppParameters "--db C:\caminho\integration.db"

SUPORTE
-------

Logs tecnicos:
  logs/service.log
  logs/service_error.log

Configuracao ativa:
  Abrir dashboard > Configuracao > Ver conexoes

Problemas comuns:
  - Porta 8000 ja em uso: definir outra porta
  - Permissoes de pasta: instalar em local com permissoes total
  - Generix Mailbox nao encontrado: verificar caminho em Configuracao
