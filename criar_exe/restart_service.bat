@echo off
setlocal enabledelayedexpansion

REM Reiniciar servico RelatoriosEncomendasEDI
REM Util para resolver problemas de BD locked ou 500 errors

cd /d "%~dp0"

if not exist "nssm.exe" (
    echo [ERRO] nssm.exe nao encontrado nesta pasta
    pause
    exit /b 1
)

echo [PARANDO] Servico...
nssm stop RelatoriosEncomendasEDI
if errorlevel 1 (
    echo [AVISO] Servico pode nao estar em execucao
)

REM Aguardar 2 segundos para liberar locks
timeout /t 2

REM Limpar temporary files
if exist "data\*.db-journal" (
    echo [LIMPANDO] Ficheiros temporarios...
    del /q "data\*.db-journal" 2>nul
    del /q "data\*.db-wal" 2>nul
)

echo [INICIANDO] Servico...
nssm start RelatoriosEncomendasEDI

if errorlevel 1 (
    echo [ERRO] Falha ao iniciar servico
    echo Verifique logs\service_error.log
    pause
    exit /b 1
)

echo [OK] Servico reiniciado com sucesso
echo Aguardando inicializacao (5s)...
timeout /t 5 /nobreak

echo [TESTANDO] Verificando saude...
timeout /t 2

REM Tentar health check
powershell -Command "try { $resp = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/health' -UseBasicParsing -ErrorAction Stop; Write-Host '[OK] Servico respondendo'; exit 0 } catch { Write-Host '[ERRO] Servico nao responde'; exit 1 }"

if errorlevel 1 (
    echo [AVISO] Servico pode ainda estar inicializando
    echo Aguarde 10 segundos e tente novamente
    echo Verifique: http://127.0.0.1:8000
)

pause
