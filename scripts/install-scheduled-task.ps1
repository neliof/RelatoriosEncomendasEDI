param(
    [string]$TaskName = "RelatoriosEncomendasEDI_EF",
    [string]$ProjectRoot = "C:\Users\TI\Desktop\RelatoriosEncomendasEDI_EF",
    [ValidateSet("Minutes", "Daily")]
    [string]$Schedule = "Minutes",
    [ValidateRange(1, 1440)]
    [int]$EveryMinutes = 10,
    [string]$DailyAt = "08:00",
    [int]$RetentionDays = 30,
    [switch]$DisableCleanup,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$DailyScript = Join-Path $ProjectRoot "scripts\run-daily.ps1"
if (-not (Test-Path $DailyScript)) {
    throw "Script diario nao encontrado: $DailyScript"
}

$ActionArgs = @(
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    "`"$DailyScript`"",
    "-RetentionDays",
    $RetentionDays
)

if ($DisableCleanup) {
    $ActionArgs += "-DisableCleanup"
}

if ($Schedule -eq "Daily") {
    $DailyTime = [DateTime]::ParseExact($DailyAt, "HH:mm", $null)
    $TriggerDescription = "Daily at $DailyAt"
} else {
    $StartAt = (Get-Date).AddMinutes(1)
    $TriggerDescription = "Every $EveryMinutes minute(s)"
}

$PasswordFromProcess = [Environment]::GetEnvironmentVariable("PRIMEIRA_LIGACAO_FTP_PASSWORD", "Process")
$PasswordFromUser = [Environment]::GetEnvironmentVariable("PRIMEIRA_LIGACAO_FTP_PASSWORD", "User")
if (-not $PasswordFromProcess -and -not $PasswordFromUser) {
    Write-Warning "A variavel PRIMEIRA_LIGACAO_FTP_PASSWORD nao esta definida para o utilizador actual. A tarefa pode falhar no FTP ate esta variavel existir."
}

Write-Output "Task: $TaskName"
Write-Output "Project: $ProjectRoot"
Write-Output "Action: powershell.exe $($ActionArgs -join ' ')"
Write-Output "Schedule: $TriggerDescription"
Write-Output "Retention: $RetentionDays day(s)"

if ($DryRun) {
    Write-Output "DryRun: no task was created or updated."
    exit 0
}

if ($Schedule -eq "Daily") {
    $Trigger = New-ScheduledTaskTrigger -Daily -At $DailyTime
} else {
    $Trigger = New-ScheduledTaskTrigger `
        -Once `
        -At $StartAt `
        -RepetitionInterval (New-TimeSpan -Minutes $EveryMinutes) `
        -RepetitionDuration (New-TimeSpan -Days 3650)
}

$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument ($ActionArgs -join " ") `
    -WorkingDirectory $ProjectRoot

$Principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel LeastPrivilege

$Settings = New-ScheduledTaskSettingsSet `
    -MultipleInstances IgnoreNew `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Principal $Principal `
    -Settings $Settings `
    -Description "Envia encomendas EDI/XML por FTP/SFTP e gera relatorios operacionais." `
    -Force | Out-Null

Write-Output "Scheduled task created or updated."
