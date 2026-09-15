param(
    [string]$PasswordEnvName = "PRIMEIRA_LIGACAO_FTP_PASSWORD",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

Write-Output "Variable: $PasswordEnvName"
Write-Output "Target: User environment"

if ($DryRun) {
    Write-Output "DryRun: no password was requested or stored."
    exit 0
}

$securePassword = Read-Host -Prompt "Password FTP" -AsSecureString
$plainPassword = [System.Net.NetworkCredential]::new("", $securePassword).Password

try {
    [Environment]::SetEnvironmentVariable($PasswordEnvName, $plainPassword, "User")
    Set-Item -Path "Env:$PasswordEnvName" -Value $plainPassword
    Write-Output "Password variable stored for the current Windows user."
    Write-Output "Open a new PowerShell session before running scheduled tasks manually."
}
finally {
    $plainPassword = $null
    $securePassword.Dispose()
}
