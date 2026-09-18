# Compilação de Executável — RelatoriosEncomendasEDI

Pasta para criação de distribuição Windows standalone.

## Requisitos

- Python 3.10+
- PyInstaller: `pip install pyinstaller`
- NSSM (para Windows Services): https://nssm.cc/download

## Build Rápido

```powershell
# Instalar dependências (uma única vez)
pip install pyinstaller apscheduler uvicorn fastapi

# Compilar (cria /release/RelatoriosEncomendasEDI/)
python build_exe.py

# Compilar single-file EXE (mais lento, mas portable)
python build_exe.py --onefile

# Limpar builds anteriores antes de compilar
python build_exe.py --clean
```

## Estrutura de Output

```
criar_exe/
├── release/
│   └── RelatoriosEncomendasEDI/
│       ├── RelatoriosEncomendasEDI.exe     (executável principal)
│       ├── nssm.exe                        (gestor de serviços)
│       ├── install_service.bat
│       ├── uninstall_service.bat
│       ├── _internal/                      (dependências)
│       ├── data/                           (BD em produção)
│       ├── logs/
│       ├── reports/
│       └── config.example.yaml
├── build/                                  (intermediários, pode deletar)
├── build_specs/                            (specs PyInstaller, pode deletar)
└── build_exe.py                            (este script)
```

## Instalação em Produção

1. Copiar `release/RelatoriosEncomendasEDI/` para `C:\Program Files\RelatoriosEncomendasEDI`

2. Abrir Command Prompt como Administrador e executar:
   ```bat
   cd C:\Program Files\RelatoriosEncomendasEDI
   install_service.bat
   ```

3. Dashboard disponível em: http://127.0.0.1:8000

## Desinstalação

```bat
uninstall_service.bat
```

## Troubleshooting

**"ModuleNotFoundError: No module named 'integration_app'"**
- Garantir que `src/` está no path do PyInstaller
- Verificar que `--paths` aponta para PROJECT_ROOT/src

**"FileNotFoundError: static/ not found"**
- Verificar que `--add-data` copia corretamente
- Tentar: `pyinstaller --noconfirm --onedir --clean ...`

**Arquivo .exe muito grande (>300MB)**
- Normal com dependências Python + FastAPI
- Usar `--onefile` se preferir arquivo único

**Port 8000 already in use**
- Iniciar com porta diferente:
  ```powershell
  .\RelatoriosEncomendasEDI.exe --port 8001
  ```

## Atualização de Releases

1. Fazer commit das mudanças no Git
2. Executar `python build_exe.py`
3. Testar em desenvolvimento
4. Copiar `release/RelatoriosEncomendasEDI/` para produção
5. Executar: `nssm restart RelatoriosEncomendasEDI`

## Notas

- NSSM gerencia auto-restart, logs, e serviço Windows
- Dados persistem em `data/` (não afetados por atualizações)
- Backup recomendado: `data/integration.db`
