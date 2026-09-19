param(
  [switch]$SkipCua,
  [switch]$SkipGoose,
  [switch]$SkipArise,
  [string]$InstallRoot = "E:\KRISHNA\tools"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Write-Step([string]$Text) { Write-Host "[KRISHNA] $Text" -ForegroundColor Cyan }
function Write-Ok([string]$Text) { Write-Host "[OK] $Text" -ForegroundColor Green }
function Write-Warn([string]$Text) { Write-Host "[WARN] $Text" -ForegroundColor Yellow }
function Has-Cmd([string]$Name) { return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue) }
function Run-Checked {
  param([Parameter(Mandatory=$true)][string]$Exe,[Parameter(Mandatory=$false)][string[]]$Arguments=@())
  & $Exe @Arguments
  $code=$LASTEXITCODE; if ($null -eq $code) { $code=0 }
  if ($code -ne 0) { throw "$Exe failed with exit code $code" }
}

$KrishnaRoot = Split-Path -Parent $PSScriptRoot
$InstallRoot = [System.IO.Path]::GetFullPath($InstallRoot)
$ConfigRoot = Join-Path $KrishnaRoot "config"
$RuntimeRoot = Join-Path $KrishnaRoot "runtime"
$ShadowRoot = Join-Path $KrishnaRoot "shadow"
$LogRoot = Join-Path $KrishnaRoot "logs"
$NpmRoot = Join-Path $InstallRoot "npm"
$PythonRoot = Join-Path $InstallRoot "python"
$CbmRoot = "E:\KRISHNA-CBM"
$CuaRoot = Join-Path $InstallRoot "cua"
$AriseRoot = Join-Path $InstallRoot "ARISE"
$GooseRoot = Join-Path $InstallRoot "goose"

@($InstallRoot,$ConfigRoot,$RuntimeRoot,$ShadowRoot,$LogRoot,$NpmRoot,$PythonRoot,$CuaRoot,$AriseRoot,$GooseRoot) | ForEach-Object { New-Item -ItemType Directory -Force -Path $_ | Out-Null }
if (-not (Test-Path $CbmRoot)) { New-Item -ItemType Directory -Force -Path $CbmRoot | Out-Null }

Write-Step "Checking prerequisites"
if (-not (Has-Cmd "git")) { throw "Git is required." }
if (-not (Has-Cmd "python")) { throw "Python 3.10+ is required." }
if (-not (Has-Cmd "npm")) { throw "Node.js/npm is required." }

Write-Step "Installing mythos-agent into $NpmRoot"
Run-Checked -Exe "npm" -Arguments @("install","-g","--prefix",$NpmRoot,"mythos-agent")

Write-Step "Installing CALM into $NpmRoot"
Run-Checked -Exe "npm" -Arguments @("install","-g","--prefix",$NpmRoot,"@eilodon/calm-mcp")

Write-Step "Creating shared KRISHNA Python agent environment"
$AgentVenv = Join-Path $PythonRoot "agents"
if (-not (Test-Path $AgentVenv)) { Run-Checked -Exe "python" -Arguments @("-m","venv",$AgentVenv) }
$AgentPython = Join-Path $AgentVenv "Scripts\python.exe"
Run-Checked -Exe $AgentPython -Arguments @("-m","pip","install","--upgrade","pip")
Run-Checked -Exe $AgentPython -Arguments @("-m","pip","install","--upgrade","mini-swe-agent","swe-rex")

Write-Step "Hardening dedicated NTFS location for codebase-memory"
try {
  if (Test-Path $CbmRoot) {
    & icacls $CbmRoot /inheritance:r | Out-Null
    & icacls $CbmRoot /grant:r "$env:USERNAME:(OI)(CI)F" "SYSTEM:(OI)(CI)F" "Administrators:(OI)(CI)F" | Out-Null
  }
} catch {
  Write-Warn "Could not fully harden ACLs automatically: $($_.Exception.Message)"
}

Write-Step "Installing codebase-memory-mcp into $CbmRoot"
$cbmInstaller = Join-Path $env:TEMP "krishna-codebase-memory-install.ps1"
Invoke-WebRequest -UseBasicParsing -Uri "https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/main/install.ps1" -OutFile $cbmInstaller
powershell -NoProfile -ExecutionPolicy Bypass -File $cbmInstaller "--dir=$CbmRoot" --skip-config
if ($LASTEXITCODE -ne 0 -and -not (Test-Path (Join-Path $CbmRoot "codebase-memory-mcp.exe"))) { throw "codebase-memory-mcp install failed" }

if (-not $SkipCua) {
  Write-Step "Installing CUA Driver into $CuaRoot"
  $env:CUA_DRIVER_RS_INSTALL_DIR = Join-Path $CuaRoot "bin"
  $env:CUA_DRIVER_RS_HOME = Join-Path $CuaRoot "home"
  $cuaInstaller = Join-Path $env:TEMP "krishna-cua-driver-install.ps1"
  Invoke-WebRequest -UseBasicParsing -Uri "https://cua.ai/driver/install.ps1" -OutFile $cuaInstaller
  powershell -NoProfile -ExecutionPolicy Bypass -File $cuaInstaller -NoPathUpdate
  if ($LASTEXITCODE -ne 0) { Write-Warn "CUA installation failed; continuing." }
}

if (-not $SkipArise) {
  Write-Step "Installing ARISE into $AriseRoot"
  if (-not (Test-Path (Join-Path $AriseRoot ".git"))) { Run-Checked -Exe "git" -Arguments @("clone","https://github.com/FARD-Lab/ARISE.git",$AriseRoot) }
  else { Run-Checked -Exe "git" -Arguments @("-C",$AriseRoot,"pull","--ff-only") }
  $AriseVenv = Join-Path $AriseRoot ".venv"
  if (-not (Test-Path $AriseVenv)) { Run-Checked -Exe "python" -Arguments @("-m","venv",$AriseVenv) }
  $ArisePython = Join-Path $AriseVenv "Scripts\python.exe"
  Run-Checked -Exe $ArisePython -Arguments @("-m","pip","install","--upgrade","pip")
  Run-Checked -Exe $ArisePython -Arguments @("-m","pip","install","-e",$AriseRoot)
}

if (-not $SkipGoose) {
  Write-Step "Installing Goose into $GooseRoot"
  $env:GOOSE_BIN_DIR = Join-Path $GooseRoot "bin"
  $env:CONFIGURE = "false"
  $gooseInstaller = Join-Path $env:TEMP "krishna-goose-install.ps1"
  Invoke-WebRequest -UseBasicParsing -Uri "https://raw.githubusercontent.com/aaif-goose/goose/main/download_cli.ps1" -OutFile $gooseInstaller
  powershell -NoProfile -ExecutionPolicy Bypass -File $gooseInstaller
  if ($LASTEXITCODE -ne 0) { Write-Warn "Goose installation failed; continuing." }
}

$npmBin = $NpmRoot
$mythosCmd = Join-Path $npmBin "mythos-agent.cmd"
$calmCmd = Join-Path $npmBin "calm.cmd"
$miniCmd = Join-Path $AgentVenv "Scripts\mini.exe"
$sweRexCmd = Join-Path $AgentVenv "Scripts\swe-rex.exe"
$cbmCmd = Join-Path $CbmRoot "codebase-memory-mcp.exe"
$cuaCmd = Join-Path $CuaRoot "bin\cua-driver.exe"
$arisePython = Join-Path $AriseRoot ".venv\Scripts\python.exe"
$gooseCmd = Join-Path $GooseRoot "bin\goose.exe"

$envFile = Join-Path $ConfigRoot "mythos-stack.env"
@(
  "KRISHNA_CODEBASE_MEMORY_CMD=$cbmCmd",
  "KRISHNA_CALM_CMD=$calmCmd",
  "KRISHNA_MYTHOS_AGENT_CMD=$mythosCmd",
  "KRISHNA_MINI_SWE_CMD=$miniCmd",
  "KRISHNA_SWE_REX_CMD=$sweRexCmd",
  "KRISHNA_ARISE_CMD=$arisePython",
  "KRISHNA_CUA_CMD=$cuaCmd",
  "KRISHNA_GOOSE_CMD=$gooseCmd",
  "KRISHNA_SHADOW_ROOT=$ShadowRoot",
  "KRISHNA_RUNTIME_ROOT=$RuntimeRoot",
  "KRISHNA_LOG_ROOT=$LogRoot"
) | Set-Content -Encoding UTF8 $envFile

Write-Ok "All KRISHNA tools targeted under $InstallRoot"
Write-Host "Config: $envFile"
Write-Host "Next run: scripts\verify-mythos-stack.ps1"