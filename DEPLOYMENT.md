# Deployment Guide — RelatoriosEncomendasEDI

Guia completo para compilar, testar e instalar em produção.

---

## 📋 Pre-requisitos

### Desenvolvedor (Build)
- Windows 7+, Windows Server 2012+
- Python 3.10+ (https://www.python.org)
- PyInstaller: `pip install pyinstaller`
- NSSM (Windows Service Manager): https://nssm.cc/download

### Utilizador Final (Runtime)
- Windows 7+, Windows Server 2012+
- .NET Framework 4.0+ (normalmente pré-instalado)
- Acesso administrativo (para instalar serviço)
- Porta 8000 disponível (ou configurar outra)

---

## 🔨 Build Process

### 1. Preparar Ambiente (Desenvolvedor)

```powershell
# Clone repo
git clone https://github.com/neliof/RelatoriosEncomendasEDI.git
cd RelatoriosEncomendasEDI

# Criar venv
python -m venv .venv
.venv\Scripts\Activate.ps1

# Instalar dependências
pip install -e .
pip install pyinstaller

# Preparar builder
cd criar_exe
```

### 2. Compilar Executável

```powershell
# Opção A: Pasta independente (recomendado)
python build_exe.py

# Opção B: Arquivo único EXE (mais lento)
python build_exe.py --onefile

# Opção C: Automated setup (recomendado para utilizadores)
setup.bat
```

**Output:**
```
criar_exe/release/RelatoriosEncomendasEDI/
├── RelatoriosEncomendasEDI.exe
├── _internal/                    (dependências)
├── data/                         (BD)
├── logs/
├── reports/
├── install_service.bat
├── uninstall_service.bat
└── README_PRODUCAO.txt
```

### 3. Testar Localmente

```powershell
cd release/RelatoriosEncomendasEDI

# Executar diretamente (sem serviço)
.\RelatoriosEncomendasEDI.exe

# Abrir em browser
http://127.0.0.1:8000

# Testar endpoints
curl http://127.0.0.1:8000/health
```

---

## 📦 Deployment em Produção

### Instalação Simples (Manual)

1. **Copiar para Servidor:**
   ```powershell
   # De desenvolvedor
   Copy-Item -Recurse "release/RelatoriosEncomendasEDI" "\\servidor\c$\Program Files"
   ```

2. **Preparar NSSM:**
   ```powershell
   # Descarregar NSSM
   # https://nssm.cc/download
   
   # Copiar nssm.exe para pasta
   Copy-Item "nssm.exe" "C:\Program Files\RelatoriosEncomendasEDI"
   ```

3. **Instalar Serviço (como Admin):**
   ```powershell
   cd "C:\Program Files\RelatoriosEncomendasEDI"
   .\install_service.bat
   ```

4. **Verificar:**
   ```powershell
   # Dashboard deve estar online em:
   # http://<IP_servidor>:8000
   
   # Verificar serviço
   Get-Service RelatoriosEncomendasEDI
   ```

### Instalação Corporativa (Script)

Para rollout em múltiplos servidores:

```powershell
# deploy.ps1
$InstallPath = "C:\Program Files\RelatoriosEncomendasEDI"
$SourcePath = "\\share\releases\RelatoriosEncomendasEDI"

Copy-Item -Recurse $SourcePath $InstallPath -Force
Copy-Item "\\share\tools\nssm.exe" "$InstallPath\nssm.exe"

Push-Location $InstallPath
.\install_service.bat
Pop-Location

# Aguardar inicialização
Start-Sleep -Seconds 5

# Testar
$response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -ErrorAction SilentlyContinue
if ($response.StatusCode -eq 200) {
    Write-Host "✓ Deployment OK"
} else {
    Write-Host "✗ Deployment FAILED"
}
```

---

## 🔄 Atualizações

### Update Simples

1. **Compilar nova versão:**
   ```powershell
   cd criar_exe
   python build_exe.py --clean
   ```

2. **Stop serviço:**
   ```powershell
   nssm stop RelatoriosEncomendasEDI
   ```

3. **Backup dados (recomendado):**
   ```powershell
   Copy-Item "C:\Program Files\RelatoriosEncomendasEDI\data\integration.db" `
             "C:\Program Files\RelatoriosEncomendasEDI\data\integration.db.backup"
   ```

4. **Atualizar EXE:**
   ```powershell
   Copy-Item "release\RelatoriosEncomendasEDI\RelatoriosEncomendasEDI.exe" `
             "C:\Program Files\RelatoriosEncomendasEDI\RelatoriosEncomendasEDI.exe" -Force
   ```

5. **Reiniciar:**
   ```powershell
   nssm start RelatoriosEncomendasEDI
   ```

### Rollback Emergencial

```powershell
# Se update falhar:
nssm stop RelatoriosEncomendasEDI

# Restaurar versão anterior
Copy-Item "C:\Program Files\RelatoriosEncomendasEDI\backup\RelatoriosEncomendasEDI.exe.old" `
          "C:\Program Files\RelatoriosEncomendasEDI\RelatoriosEncomendasEDI.exe"

# Restaurar DB se necessário
Copy-Item "C:\Program Files\RelatoriosEncomendasEDI\data\integration.db.backup" `
          "C:\Program Files\RelatoriosEncomendasEDI\data\integration.db" -Force

nssm start RelatoriosEncomendasEDI
```

---

## 📊 Monitoramento

### Health Check

```powershell
# Manual
curl http://127.0.0.1:8000/health

# PowerShell
$health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health"
$health | ConvertTo-Json
```

### Logs

```powershell
# Service logs (NSSM)
Get-Content "C:\Program Files\RelatoriosEncomendasEDI\logs\service.log"
Get-Content "C:\Program Files\RelatoriosEncomendasEDI\logs\service_error.log"

# Real-time (tail)
Get-Content -Path "logs\service.log" -Wait
```

### Windows Event Viewer

```powershell
# Ver erros do serviço
Get-EventLog -LogName System -Source NSSM -Newest 10
```

---

## 🔐 Segurança

### Firewall

```powershell
# Permitir porta 8000 (Windows Firewall)
New-NetFirewallRule -DisplayName "RelatoriosEncomendasEDI" `
  -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8000
```

### Credenciais

```powershell
# Definir password admin (ao arrancar serviço)
$env:INTEGRATION_ADMIN_PASSWORD = "sua_senha_forte"

# Para persistir, adicionar ao serviço:
nssm set RelatoriosEncomendasEDI AppEnvironmentExtra INTEGRATION_ADMIN_PASSWORD=sua_senha_forte
```

### Folder Permissions

```powershell
# Usar conta de serviço dedicada (melhor prática)
New-LocalUser -Name "svc-edi" -Description "EDI Service Account" -Password (ConvertTo-SecureString "password" -AsPlainText -Force) -PasswordNeverExpires

# Atribuir permissões
icacls "C:\Program Files\RelatoriosEncomendasEDI" /grant "svc-edi:(OI)(CI)F" /T

# Configurar serviço para usar conta
nssm set RelatoriosEncomendasEDI ObjectName "svc-edi" "password"
```

---

## ❌ Troubleshooting

### Porta 8000 já em uso

```powershell
# Encontrar processo
Get-NetTCPConnection -LocalPort 8000 | Select OwningProcess, State

# Usar porta diferente
nssm set RelatoriosEncomendasEDI AppParameters "--port 8001"
nssm restart RelatoriosEncomendasEDI
```

### Serviço não inicia

```powershell
# Verificar logs
Get-Content "logs\service_error.log"

# Testar executável diretamente
cd "C:\Program Files\RelatoriosEncomendasEDI"
.\RelatoriosEncomendasEDI.exe

# Se falha, reinstalar
.\uninstall_service.bat
.\install_service.bat
```

### Database locked

```powershell
# Restart serviço (liberta lock)
nssm restart RelatoriosEncomendasEDI

# Se persistir, eliminar temp files
Remove-Item "data\*.db-journal"
Remove-Item "data\*.db-wal"
```

---

## 📝 Checklist de Deployment

- [ ] Compilar EXE com `python build_exe.py`
- [ ] Testar localmente em desenvolvimento
- [ ] Backup dados em produção (se update)
- [ ] Copiar para servidor (ou usar script corporativo)
- [ ] Descarregar e copiar NSSM
- [ ] Executar `install_service.bat` como Admin
- [ ] Testar health endpoint: `curl http://127.0.0.1:8000/health`
- [ ] Configurar firewall (porta 8000)
- [ ] Configurar logging/monitoramento
- [ ] Documentar credenciais admin
- [ ] Testar failover (restart, auto-start)
- [ ] Criar backup de dados

---

## 📞 Suporte

Problemas?

1. Verificar logs: `logs/service.log`
2. Testar manual: `.\RelatoriosEncomendasEDI.exe --port 8000`
3. Consultar GitHub issues: https://github.com/neliof/RelatoriosEncomendasEDI/issues
4. Contactar TIC SOL

---

**Versão:** 1.0  
**Última atualização:** 2026-09-18  
**Status:** Production Ready
