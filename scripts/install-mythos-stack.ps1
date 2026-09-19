param(
  [switch]$SkipCua,
  [switch]$SkipGoose,
  [switch]$SkipArise,
  [string]$InstallRoot = "$env:USERPROFILE\.krishna\tools"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Write-Step([string]$Text) { Write-Host "[KRISHNA] $Text" -ForegroundColor Cyan }
function Write-Ok([string]$Text) { Write-Host "[OK] $Text" -ForegroundColor Green }
function Write-Warn([string]$Text) { Write-Host "[WARN] $Text" -ForegroundColor Yellow }
function Has-Cmd([string]$Name) { return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue) }
function Run-Checked([string]$Exe, [string[]]$Args) { & $Exe @Args; if ($LASTEXITCODE -ne 0) { throw "$Exe failed with exit code $LASTEXITCODE" } }

New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null

Write-Step "Checking prerequisites"
if (-not (Has-Cmd "git")) { throw "Git is required. Install Git for Windows first." }
if (-not (Has-Cmd "python")) { throw "Python 3.10+ is required." }
if (-not (Has-Cmd "npm")) { throw "Node.js/npm is required." }

Write-Step "Installing mythos-agent"
Run-Checked "npm" @("install","-g","mythos-agent")
Write-Ok "mythos-agent installed"

Write-Step "Installing CALM MCP"
Run-Checked "npm" @("install","-g","@eilodon/calm-mcp")
Write-Ok "CALM installed"

Write-Step "Installing mini-SWE-agent"
Run-Checked "python" @("-m","pip","install","--upgrade","mini-swe-agent")
Write-Ok "mini-SWE-agent installed"

Write-Step "Installing SWE-ReX"
Run-Checked "python" @("-m","pip","install","--upgrade","swe-rex")
Write-Ok "SWE-ReX installed"

Write-Step "Installing codebase-memory-mcp using the official Windows installer"
$cbmInstaller = Join-Path $env:TEMP "krishna-codebase-memory-install.ps1"
Invoke-WebRequest -UseBasicParsing -Uri "https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/main/install.ps1" -OutFile $cbmInstaller
powershell -NoProfile -ExecutionPolicy Bypass -File $cbmInstaller
if ($LASTEXITCODE -ne 0) { throw "codebase-memory-mcp installer failed" }
Write-Ok "codebase-memory-mcp installed"

if (-not $SkipCua) {
  Write-Step "Installing CUA Driver using the official Windows installer"
  $cuaInstaller = Join-Path $env:TEMP "krishna-cua-driver-install.ps1"
  Invoke-WebRequest -UseBasicParsing -Uri "https://cua.ai/driver/install.ps1" -OutFile $cuaInstaller
  powershell -NoProfile -ExecutionPolicy Bypass -File $cuaInstaller
  if ($LASTEXITCODE -eq 0) {
    Write-Ok "CUA Driver installed"
    if (Has-Cmd "cua-driver") {
      try { & cua-driver telemetry disable | Out-Host } catch { Write-Warn "Could not disable CUA telemetry automatically." }
    }
  } else { Write-Warn "CUA installation failed; KRISHNA will keep running without it." }
}

if (-not $SkipArise) {
  Write-Step "Installing ARISE into an isolated virtual environment"
  $ariseDir = Join-Path $InstallRoot "ARISE"
  if (-not (Test-Path (Join-Path $ariseDir ".git"))) {
    Run-Checked "git" @("clone","https://github.com/FARD-Lab/ARISE.git",$ariseDir)
  } else { Run-Checked "git" @("-C",$ariseDir,"pull","--ff-only") }
  $venvDir = Join-Path $ariseDir ".venv"
  if (-not (Test-Path $venvDir)) { Run-Checked "python" @("-m","venv",$venvDir) }
  $arisePython = Join-Path $venvDir "Scripts\python.exe"
  Run-Checked $arisePython @("-m","pip","install","--upgrade","pip")
  Run-Checked $arisePython @("-m","pip","install","-e",$ariseDir)
  Write-Ok "ARISE installed in $venvDir"
}

if (-not $SkipGoose) {
  Write-Step "Installing Goose CLI when bash is available"
  $bash = Get-Command bash -ErrorAction SilentlyContinue
  if ($bash) {
    & $bash.Source -lc "curl -fsSL https://github.com/aaif-goose/goose/releases/download/stable/download_cli.sh | bash"
    if ($LASTEXITCODE -eq 0) { Write-Ok "Goose CLI installed" } else { Write-Warn "Goose installer returned exit code $LASTEXITCODE" }
  } else { Write-Warn "Bash not found. Goose CLI skipped; install Git Bash/MSYS2 or Goose Desktop later." }
}

$envFile = Join-Path $env:USERPROFILE ".krishna\mythos-stack.env"
New-Item -ItemType Directory -Force -Path (Split-Path $envFile) | Out-Null
@(
  "KRISHNA_CODEBASE_MEMORY_CMD=codebase-memory-mcp",
  "KRISHNA_CALM_CMD=calm",
  "KRISHNA_MYTHOS_AGENT_CMD=mythos-agent",
  "KRISHNA_MINI_SWE_CMD=mini",
  "KRISHNA_SWE_REX_CMD=swe-rex",
  "KRISHNA_ARISE_CMD=arise",
  "KRISHNA_CUA_CMD=cua",
  "KRISHNA_GOOSE_CMD=goose"
) | Set-Content -Encoding UTF8 $envFile

Write-Ok "Bootstrap complete"
Write-Host "Next run: scripts\verify-mythos-stack.ps1 and scripts\discover-krishna-projects.ps1"