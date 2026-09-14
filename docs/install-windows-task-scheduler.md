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

## Agendamento

No Task Scheduler, criar uma tarefa com:

- Program/script: caminho para `.venv\Scripts\python.exe`.
- Arguments: `-m integration_app.app run-once --config C:\caminho\config.yaml`.
- Start in: pasta raiz do projecto.
- Trigger: intervalo operacional escolhido, por exemplo 5 minutos.

## Verificacao

Confirmar que existem ficheiros em:

- `logs`
- `reports`
- `data/integration.db`
