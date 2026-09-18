@echo off
setlocal enabledelayedexpansion

REM Instalar RelatoriosEncomendasEDI como Windows Service
REM Requer: NSSM.exe na mesma pasta
REM Requer: Executar como Administrador

cd /d "%~dp0"

if not exist "nssm.exe" (
    echo [ERRO] nssm.exe nao encontrado nesta pasta
    echo Copie nssm.exe de: https://nssm.cc/download
    pause
    exit /b 1
)

if not exist "RelatoriosEncomendasEDI.exe" (
    echo [ERRO] RelatoriosEncomendasEDI.exe nao encontrado nesta pasta
    pause
    exit /b 1
)

echo [INSTALANDO] Servico RelatoriosEncomendasEDI...
nssm install RelatoriosEncomendasEDI "%cd%\RelatoriosEncomendasEDI.exe"

if errorlevel 1 (
    echo [ERRO] Falha ao instalar servico
    pause
    exit /b 1
)

REM Configurar para iniciar na boot
nssm set RelatoriosEncomendasEDI Start SERVICE_AUTO_START

REM Definir working directory
nssm set RelatoriosEncomendasEDI AppDirectory "%cd%"

REM Enviar output para logs
nssm set RelatoriosEncomendasEDI AppStdout "%cd%\logs\service.log"
nssm set RelatoriosEncomendasEDI AppStderr "%cd%\logs\service_error.log"

REM Auto-restart se falhar
nssm set RelatoriosEncomendasEDI AppExit Default Restart

echo [INICIANDO] Servico...
nssm start RelatoriosEncomendasEDI

if errorlevel 1 (
    echo [ERRO] Falha ao iniciar servico
    pause
    exit /b 1
)

echo.
echo [OK] Servico instalado e iniciado com sucesso!
echo.
echo Dashboard disponivel em: http://127.0.0.1:8000
echo.
pause
