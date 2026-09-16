# Instalacao no Windows Task Scheduler

## Preparacao

1. Instalar Python 3.11 ou superior.
2. Criar ambiente virtual: `python -m venv .venv`.
3. Activar ambiente: `.venv\Scripts\Activate.ps1`.
4. Instalar dependencias: `python -m pip install -e .[dev]`.
5. Copiar `config.example.yaml` para `config.yaml`.
6. Configurar a password FTP usada no YAML.

Opcao recomendada: gravar a password num ficheiro secret DPAPI do Windows, protegido pelo utilizador actual:

```powershell
powershell.exe -ExecutionPolicy Bypass -File "C:\Users\TI\Desktop\RelatoriosEncomendasEDI_EF\scripts\set-ftp-password-secret.ps1"
```

Este comando cria `secrets\PRIMEIRA_LIGACAO_FTP_PASSWORD.secret`. A pasta `secrets/` esta ignorada pelo git. O `run-daily.ps1` carrega este secret apenas para o processo da tarefa agendada quando a variavel `PRIMEIRA_LIGACAO_FTP_PASSWORD` nao existir.

Alternativa: gravar a password FTP no ambiente do utilizador Windows:

```powershell
powershell.exe -ExecutionPolicy Bypass -File "C:\Users\TI\Desktop\RelatoriosEncomendasEDI_EF\scripts\set-ftp-password-user.ps1"
```

Este comando pede a password no terminal e guarda a variavel `PRIMEIRA_LIGACAO_FTP_PASSWORD` no perfil do utilizador. Depois de executar, abrir uma nova sessao PowerShell antes de testar manualmente.

## Execucao Manual

```powershell
python -m integration_app.app run-once --config config.yaml
```

Para correr o ciclo diario completo, com envio e relatorio Generix:

```powershell
powershell.exe -ExecutionPolicy Bypass -File "C:\Users\TI\Desktop\RelatoriosEncomendasEDI_EF\scripts\run-daily.ps1"
```

O script:

- usa `.venv\Scripts\python.exe` quando existir;
- define `PYTHONPATH=src`;
- carrega `secrets\PRIMEIRA_LIGACAO_FTP_PASSWORD.secret`, se existir e a variavel de ambiente ainda nao estiver definida;
- executa `run-once --config config.yaml`;
- executa `generix-report`;
- grava transcript em `logs\run-daily-YYYYMMDD-HHMMSS.log`;
- remove relatorios e logs com mais de 30 dias, salvo configuracao diferente;
- devolve erro ao Task Scheduler se algum comando falhar.

## Agendamento

Opcao recomendada: instalar ou actualizar a tarefa pelo script incluido.

Para simular sem alterar o Windows:

```powershell
powershell.exe -ExecutionPolicy Bypass -File "C:\Users\TI\Desktop\RelatoriosEncomendasEDI_EF\scripts\install-scheduled-task.ps1" -Schedule Minutes -EveryMinutes 10 -DryRun
```

Para instalar de 10 em 10 minutos:

```powershell
powershell.exe -ExecutionPolicy Bypass -File "C:\Users\TI\Desktop\RelatoriosEncomendasEDI_EF\scripts\install-scheduled-task.ps1" -Schedule Minutes -EveryMinutes 10
```

Outros exemplos:

```powershell
powershell.exe -ExecutionPolicy Bypass -File "C:\Users\TI\Desktop\RelatoriosEncomendasEDI_EF\scripts\install-scheduled-task.ps1" -Schedule Minutes -EveryMinutes 5
powershell.exe -ExecutionPolicy Bypass -File "C:\Users\TI\Desktop\RelatoriosEncomendasEDI_EF\scripts\install-scheduled-task.ps1" -Schedule Minutes -EveryMinutes 30
powershell.exe -ExecutionPolicy Bypass -File "C:\Users\TI\Desktop\RelatoriosEncomendasEDI_EF\scripts\install-scheduled-task.ps1" -Schedule Minutes -EveryMinutes 60
powershell.exe -ExecutionPolicy Bypass -File "C:\Users\TI\Desktop\RelatoriosEncomendasEDI_EF\scripts\install-scheduled-task.ps1" -Schedule Daily -DailyAt 08:00
```

Se preferires criar manualmente no Task Scheduler:

- Program/script: `powershell.exe`.
- Arguments: `-ExecutionPolicy Bypass -File "C:\Users\TI\Desktop\RelatoriosEncomendasEDI_EF\scripts\run-daily.ps1"`.
- Start in: pasta raiz do projecto.
- Trigger: horario operacional escolhido, por exemplo diario de manha.

Frequencias comuns no separador Triggers, em Advanced settings:

- `Repeat task every: 5 minutes`;
- `Repeat task every: 10 minutes`;
- `Repeat task every: 30 minutes`;
- `Repeat task every: 1 hour`;
- para X em X horas, escolher o intervalo pretendido;
- para diario, deixar sem repeticao e escolher apenas a hora.

Para alterar a retencao de relatorios/logs, acrescentar o parametro aos Arguments:

```text
-ExecutionPolicy Bypass -File "C:\Users\TI\Desktop\RelatoriosEncomendasEDI_EF\scripts\run-daily.ps1" -RetentionDays 60
```

Para desligar a limpeza automatica:

```text
-ExecutionPolicy Bypass -File "C:\Users\TI\Desktop\RelatoriosEncomendasEDI_EF\scripts\run-daily.ps1" -DisableCleanup
```

Se a password FTP estiver configurada por variavel de ambiente no `config.yaml`, confirmar que essa variavel existe no contexto do utilizador que executa a tarefa.

## Verificacao

Confirmar que existem ficheiros em:

- `logs`
- `reports`
- `data/integration.db`
