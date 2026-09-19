@echo off
setlocal enabledelayedexpansion

REM Diagnostico rapido de problemas

cd /d "%~dp0"

echo ============================================================
echo DIAGNOSTICO - RelatoriosEncomendasEDI
echo ============================================================
echo.

REM Verificar arquivos
echo [CHECK] Verificando arquivos...
if not exist "RelatoriosEncomendasEDI.exe" (
    echo [ERRO] RelatoriosEncomendasEDI.exe nao encontrado
    goto end
)
if not exist "config.yaml" (
    echo [ERRO] config.yaml nao encontrado
    echo [FIX] Copie config.example.yaml para config.yaml
    goto end
)
if not exist "nssm.exe" (
    echo [AVISO] nssm.exe nao encontrado (necessario para servico)
)
echo [OK] Arquivos principais presentes

REM Verificar servico
echo.
echo [CHECK] Status do servico...
nssm status RelatoriosEncomendasEDI >nul 2>&1
if errorlevel 0 (
    for /f "tokens=*" %%A in ('nssm status RelatoriosEncomendasEDI') do (
        echo Status: %%A
    )
) else (
    echo [INFO] Servico nao esta instalado (use install_service.bat)
)

REM Verificar porta
echo.
echo [CHECK] Porta 8000...
netstat -ano | find ":8000" >nul 2>&1
if errorlevel 0 (
    echo [OK] Porta 8000 em uso (servico rodando?)
) else (
    echo [INFO] Porta 8000 nao em uso
)

REM Testar executavel
echo.
echo [CHECK] Testando executavel...
.\RelatoriosEncomendasEDI.exe --help >nul 2>&1
if errorlevel 0 (
    echo [OK] Executavel funciona
) else (
    echo [ERRO] Executavel nao funciona
    echo Tente: .\RelatoriosEncomendasEDI.exe --help
    goto end
)

REM Testar health endpoint
echo.
echo [CHECK] Health endpoint...
powershell -Command "try { $resp = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/health' -UseBasicParsing -ErrorAction Stop; Write-Host '[OK] Servico respondendo'; Write-Host $resp.Content } catch { Write-Host '[ERRO] Servico nao responde'; Write-Host 'Inicie com: .\RelatoriosEncomendasEDI.exe' }" 2>nul

REM Verificar BD
echo.
echo [CHECK] Base de dados...
if exist "data\integration.db" (
    echo [OK] BD encontrada
) else (
    echo [INFO] BD sera criada automaticamente na primeira execucao
)

REM Verificar logs
echo.
echo [CHECK] Logs...
if exist "logs\service_error.log" (
    echo [ERROS RECENTES]:
    powershell -Command "Get-Content 'logs\service_error.log' -Tail 5 -ErrorAction SilentlyContinue"
) else (
    echo [INFO] Nenhum erro registado
)

:end
echo.
echo ============================================================
echo RESOLUCOES COMUNS:
echo.
echo HTTP 403:
echo   - Variavel INTEGRATION_ADMIN_PASSWORD nao definida
echo   - Use: install_service.bat (define password automaticamente)
echo   - Ou manualmente: nssm set RelatoriosEncomendasEDI AppEnvironmentExtra INTEGRATION_ADMIN_PASSWORD=sua_senha
echo.
echo HTTP 500:
echo   - BD pode estar locked
echo   - Use: restart_service.bat (reinicia e limpa locks)
echo   - Ou manualmente: nssm restart RelatoriosEncomendasEDI
echo.
echo config.yaml nao encontrado:
echo   - Copie config.example.yaml para config.yaml
echo   - Edit com seus parametros (host FTP, credenciais, etc)
echo.
echo Porta 8000 em uso:
echo   - Iniciar em porta diferente: .\RelatoriosEncomendasEDI.exe --port 8001
echo   - Ou mudar servico: nssm set RelatoriosEncomendasEDI AppParameters "--port 8001"
echo ============================================================
pause
