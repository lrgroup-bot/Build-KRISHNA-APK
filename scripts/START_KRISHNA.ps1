param(
    [Parameter(Mandatory=$false)][string]$KrishnaRoot = "E:\Krishna-The GOD",
    [Parameter(Mandatory=$false)][int]$Port = 8766
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$KrishnaRoot=[IO.Path]::GetFullPath($KrishnaRoot)
$coreDir=Join-Path $KrishnaRoot "core"
$py=Join-Path $KrishnaRoot ".venv\Scripts\python.exe"
$logDir=Join-Path $KrishnaRoot "logs"
if(!(Test-Path $coreDir)){throw "KRISHNA core directory not found: $coreDir"}
if(!(Test-Path $py)){throw "KRISHNA venv Python not found: $py"}
if(!(Test-Path $logDir)){New-Item -ItemType Directory -Force $logDir|Out-Null}
$env:PYTHONPATH=$coreDir
$env:KRISHNA_HOST="127.0.0.1"
$env:KRISHNA_PORT=[string]$Port
$env:KRISHNA_ALLOW_ACTIONS="1"
Write-Host ""
Write-Host "KRISHNA MODERN CORE START" -ForegroundColor Cyan
Write-Host "Root : $KrishnaRoot"
Write-Host "UI   : http://127.0.0.1:$Port/"
Write-Host ""
# Modern KRISHNA is server-first. Legacy desktop/console launchers are intentionally not preferred.
& $py -u -m krishna_core.server
exit $LASTEXITCODE
