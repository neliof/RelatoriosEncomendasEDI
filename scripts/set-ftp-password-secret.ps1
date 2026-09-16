param(
    [string]$ProjectRoot = "C:\Users\TI\Desktop\RelatoriosEncomendasEDI_EF",
    [string]$PasswordEnvName = "PRIMEIRA_LIGACAO_FTP_PASSWORD",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$SecretDir = Join-Path $ProjectRoot "secrets"
$SecretPath = Join-Path $SecretDir "$PasswordEnvName.secret"

Write-Output "Variable: $PasswordEnvName"
Write-Output "Target: DPAPI user secret file"
Write-Output "Path: $SecretPath"

if ($DryRun) {
    Write-Output "DryRun: no password was requested or stored."
    exit 0
}

$securePassword = Read-Host -Prompt "Password FTP" -AsSecureString

try {
    New-Item -ItemType Directory -Force -Path $SecretDir | Out-Null
    $securePassword | ConvertFrom-SecureString | Set-Content -Path $SecretPath -Encoding UTF8 -NoNewline
    Write-Output "Password secret stored for the current Windows user."
    Write-Output "The scheduled script can now load it without a permanent environment variable."
}
finally {
    $securePassword.Dispose()
}
