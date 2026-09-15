# Instalacao no Windows Task Scheduler

## Preparacao

1. Instalar Python 3.11 ou superior.
2. Criar ambiente virtual: `python -m venv .venv`.
3. Activar ambiente: `.venv\Scripts\Activate.ps1`.
4. Instalar dependencias: `python -m pip install -e .[dev]`.
5. Copiar `config.example.yaml` para `config.yaml`.
6. Definir variaveis de ambiente das passwords usadas no YAML.

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
- executa `run-once --config config.yaml`;
- executa `generix-report`;
- grava transcript em `logs\run-daily-YYYYMMDD-HHMMSS.log`;
- devolve erro ao Task Scheduler se algum comando falhar.

## Agendamento

No Task Scheduler, criar uma tarefa com:

- Program/script: `powershell.exe`.
- Arguments: `-ExecutionPolicy Bypass -File "C:\Users\TI\Desktop\RelatoriosEncomendasEDI_EF\scripts\run-daily.ps1"`.
- Start in: pasta raiz do projecto.
- Trigger: horario operacional escolhido, por exemplo diario de manha.

Se a password FTP estiver configurada por variavel de ambiente no `config.yaml`, confirmar que essa variavel existe no contexto do utilizador que executa a tarefa.

## Verificacao

Confirmar que existem ficheiros em:

- `logs`
- `reports`
- `data/integration.db`
