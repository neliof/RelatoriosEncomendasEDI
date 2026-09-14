param(
    [string]$ConfigPath = "config.yaml",
    [string]$PasswordEnvName = "PRIMEIRA_LIGACAO_FTP_PASSWORD"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $ConfigPath)) {
    throw "Ficheiro de configuracao nao encontrado: $ConfigPath"
}

$securePassword = Read-Host -Prompt "Password FTP" -AsSecureString
$plainPassword = [System.Net.NetworkCredential]::new("", $securePassword).Password

try {
    Set-Item -Path "Env:$PasswordEnvName" -Value $plainPassword
    Set-Item -Path "Env:PYTHONPATH" -Value "src"

    python -m integration_app.app run-once --config $ConfigPath
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
finally {
    Remove-Item -Path "Env:$PasswordEnvName" -ErrorAction SilentlyContinue
    $plainPassword = $null
    $securePassword.Dispose()
}
