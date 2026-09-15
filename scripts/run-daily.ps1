param(
    [string]$ProjectRoot = "C:\Users\TI\Desktop\RelatoriosEncomendasEDI_EF",
    [string]$ConfigPath = "C:\Users\TI\Desktop\RelatoriosEncomendasEDI_EF\config.yaml",
    [string]$GenerixStorageRoot = "C:\Users\TI\Documents\Influe-Generix\Bat\storage\cpip_20122611437260",
    [string]$ReportDir = "C:\Users\TI\Desktop\RelatoriosEncomendasEDI_EF\reports",
    [string]$LogDir = "C:\Users\TI\Desktop\RelatoriosEncomendasEDI_EF\logs",
    [string]$PythonExe = "",
    [int]$RetentionDays = 30,
    [switch]$DisableCleanup
)

$ErrorActionPreference = "Stop"
$PreviousLocation = Get-Location
$RunId = Get-Date -Format "yyyyMMdd-HHmmss"
$TranscriptPath = Join-Path $LogDir "run-daily-$RunId.log"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
Start-Transcript -Path $TranscriptPath -Append | Out-Null

try {
    Set-Location $ProjectRoot
    $env:PYTHONPATH = "src"
    if (-not $PythonExe) {
        $VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
        if (Test-Path $VenvPython) {
            $PythonExe = $VenvPython
        } else {
            $PythonExe = "python"
        }
    }

    & $PythonExe -m integration_app.app run-once --config $ConfigPath
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    & $PythonExe -m integration_app.app generix-report --storage-root $GenerixStorageRoot --report-dir $ReportDir
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    if (-not $DisableCleanup) {
        $Cutoff = (Get-Date).AddDays(-$RetentionDays)
        Get-ChildItem -Path $ReportDir -File | Where-Object { $_.LastWriteTime -lt $Cutoff } | Remove-Item -Force
        Get-ChildItem -Path $LogDir -File | Where-Object { $_.LastWriteTime -lt $Cutoff } | Remove-Item -Force
    }
} finally {
    Set-Location $PreviousLocation
    Stop-Transcript | Out-Null
}
