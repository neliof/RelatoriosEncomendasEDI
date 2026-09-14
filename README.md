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
- Windows Task Scheduler: `docs/install-windows-task-scheduler.md`
