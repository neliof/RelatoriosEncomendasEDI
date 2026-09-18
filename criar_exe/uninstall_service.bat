@echo off
setlocal enabledelayedexpansion

REM Desinstalar servico RelatoriosEncomendasEDI
REM Requer: NSSM.exe na mesma pasta
REM Requer: Executar como Administrador

cd /d "%~dp0"

if not exist "nssm.exe" (
    echo [ERRO] nssm.exe nao encontrado nesta pasta
    pause
    exit /b 1
)

echo [PARANDO] Servico RelatoriosEncomendasEDI...
nssm stop RelatoriosEncomendasEDI

if errorlevel 1 (
    echo [AVISO] Servico pode nao estar em execucao
)

echo [DESINSTALANDO] Servico...
nssm remove RelatoriosEncomendasEDI confirm

if errorlevel 1 (
    echo [ERRO] Falha ao desinstalar servico
    pause
    exit /b 1
)

echo [OK] Servico desinstalado com sucesso!
pause
