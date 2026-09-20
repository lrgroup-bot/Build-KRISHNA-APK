param([switch]$SkipStart)
$ErrorActionPreference="Stop"
$Source="E:\KRISHNA-SOURCE"; $Runtime="E:\Krishna-The GOD"; $Py="$Runtime\.venv\Scripts\python.exe"
Write-Host "=== KRISHNA ONE-PULL DEPLOY ===" -ForegroundColor Cyan
if(!(Test-Path "$Source\.git")){ throw "Source repo missing: $Source" }
if(!(Test-Path $Py)){ throw "KRISHNA venv missing: $Py" }
Set-Location $Source
if((git status --porcelain)){ throw "E:\KRISHNA-SOURCE has local changes. Refusing destructive update." }
git fetch --prune origin
git checkout main
git pull --ff-only origin main
$Head=(git rev-parse HEAD).Trim(); Write-Host "SOURCE HEAD $Head"
# Source regression before touching runtime.
& $Py -m unittest discover -s "$Source\tests"
if($LASTEXITCODE -ne 0){ throw "SOURCE TESTS FAILED; runtime unchanged." }
# Preserve runtime-owned state: no /MIR, no deletion, and explicitly exclude local state/assets.
$excludeDirs=@("__pycache__",".krishna_state","state","logs","backups",".venv","ollama-models","dashboard\assets\avatar")
$xd=@(); foreach($d in $excludeDirs){$xd+=@("/XD",(Join-Path $Runtime $d))}
& robocopy "$Source\core" "$Runtime\core" /E /R:1 /W:1 /XF "*.pyc" @xd
if($LASTEXITCODE -ge 8){ throw "CORE COPY FAILED: robocopy=$LASTEXITCODE" }
# Copy scripts without deleting local scripts.
New-Item -ItemType Directory -Force "$Runtime\scripts"|Out-Null
& robocopy "$Source\scripts" "$Runtime\scripts" /E /R:1 /W:1
if($LASTEXITCODE -ge 8){ throw "SCRIPT COPY FAILED: robocopy=$LASTEXITCODE" }
$env:PYTHONPATH="$Runtime\core"
& $Py -m unittest discover -s "$Source\tests"
if($LASTEXITCODE -ne 0){ throw "POST-DEPLOY TESTS FAILED. Do not start KRISHNA." }
# Import/compile smoke checks against deployed runtime.
& $Py -m compileall -q "$Runtime\core\krishna_core"
if($LASTEXITCODE -ne 0){ throw "DEPLOYED CORE COMPILE FAILED" }
& $Py -c "from krishna_core.orchestrator import Orchestrator; print('ORCHESTRATOR_IMPORT_OK')"
if($LASTEXITCODE -ne 0){ throw "ORCHESTRATOR IMPORT FAILED" }
Write-Host "DEPLOY VERIFIED AT $Head" -ForegroundColor Green
if(!$SkipStart){
  $env:KRISHNA_ALLOW_ACTIONS="1"
  & "$Runtime\scripts\START_KRISHNA.ps1"
}
