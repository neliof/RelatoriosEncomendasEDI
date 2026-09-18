@echo off
setlocal enabledelayedexpansion

REM Setup automatizado para compilacao e instalacao
REM Execute como Administrador para instalar como servico

echo ============================================================
echo RELATORIOS ENCOMENDAS EDI - Setup de Compilacao
echo ============================================================
echo.

REM Detectar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado. Instale Python 3.10+ primeiro.
    pause
    exit /b 1
)

echo [OK] Python encontrado
python --version

REM Verificar NSSM
if not exist "nssm.exe" (
    echo.
    echo [AVISO] nssm.exe nao encontrado nesta pasta
    echo Baixando NSSM e copie nssm.exe para: %cd%
    echo https://nssm.cc/download
    echo.
)

REM Instalar PyInstaller
echo.
echo [INSTALANDO] Dependencias...
pip install -q pyinstaller apscheduler uvicorn fastapi

if errorlevel 1 (
    echo [ERRO] Falha ao instalar dependencias
    pause
    exit /b 1
)

echo [OK] Dependencias instaladas

REM Compilar
echo.
echo [COMPILANDO] RelatoriosEncomendasEDI...
python build_exe.py

if errorlevel 1 (
    echo [ERRO] Compilacao falhou
    pause
    exit /b 1
)

echo [OK] Compilacao concluida com sucesso!
echo.
echo Pasta de release: %cd%\release\RelatoriosEncomendasEDI
echo.

REM Perguntar se instalar como servico
set /p INSTALL="Deseja instalar como Windows Service agora? (S/N) "
if /i "%INSTALL%"=="S" (
    cd /d "%cd%\release\RelatoriosEncomendasEDI"
    if exist "install_service.bat" (
        echo.
        echo [INSTALANDO] Servico...
        call install_service.bat
    ) else (
        echo [ERRO] install_service.bat nao encontrado
    )
)

echo.
echo ============================================================
echo Setup concluido!
echo ============================================================
pause
