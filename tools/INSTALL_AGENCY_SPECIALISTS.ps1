param([string]$Root="E:\Krishna-The GOD")
$ErrorActionPreference="Stop"
$dest=Join-Path $Root "external\agency-agents"
$parent=Split-Path $dest -Parent
New-Item -ItemType Directory -Force $parent | Out-Null
if(Test-Path (Join-Path $dest ".git")){
  git -C $dest fetch --depth 1 origin main
  git -C $dest reset --hard origin/main
}else{
  git clone --depth 1 https://github.com/msitarzewski/agency-agents.git $dest
}
Write-Host "Agency source installed:" $dest
Write-Host "KRISHNA indexes Markdown specialist definitions only."
Write-Host "Agency install/convert shell scripts are NOT executed."
$env:PYTHONPATH=Join-Path $Root "core"
& (Join-Path $Root ".venv\Scripts\python.exe") -c "from krishna_core.specialist_library import SpecialistLibrary; from pathlib import Path; r=Path(r'$Root'); s=SpecialistLibrary(r/'.krishna_state',r/'external'/'agency-agents'); x=s.index(); print('Indexed specialists:',x['total']); print('Divisions:',len(x['divisions']))"
