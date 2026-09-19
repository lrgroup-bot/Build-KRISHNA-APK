param([string]$KrishnaRoot = "E:\KRISHNA")
$ErrorActionPreference = "Continue"
$ConfigFile = Join-Path $KrishnaRoot "config\mythos-stack.env"
$OutputPath = Join-Path $KrishnaRoot "runtime\mythos-stack-status.json"
New-Item -ItemType Directory -Force -Path (Split-Path $OutputPath) | Out-Null

$map = @{}
if (Test-Path $ConfigFile) {
  Get-Content $ConfigFile | ForEach-Object {
    $line=$_.Trim()
    if ($line -and -not $line.StartsWith('#') -and $line.Contains('=')) {
      $parts=$line.Split('=',2); $map[$parts[0].Trim()]=$parts[1].Trim()
    }
  }
}

$specs = @(
  @{name='codebase_memory'; key='KRISHNA_CODEBASE_MEMORY_CMD'; args=@('--version')},
  @{name='calm'; key='KRISHNA_CALM_CMD'; args=@('--version')},
  @{name='mythos_agent'; key='KRISHNA_MYTHOS_AGENT_CMD'; args=@('--version')},
  @{name='mini_swe'; key='KRISHNA_MINI_SWE_CMD'; args=@('--help')},
  @{name='swe_rex'; key='KRISHNA_SWE_REX_CMD'; args=@('--help')},
  @{name='arise'; key='KRISHNA_ARISE_CMD'; args=@('-c','import arise; print(getattr(arise,"__version__","installed"))')},
  @{name='cua'; key='KRISHNA_CUA_CMD'; args=@('--help')},
  @{name='goose'; key='KRISHNA_GOOSE_CMD'; args=@('--version')}
)

$results=@()
foreach($spec in $specs){
  $cmd=$map[$spec.key]
  if(-not $cmd -or -not (Test-Path $cmd)){
    $results += [pscustomobject]@{name=$spec.name;available=$false;command=$cmd;version=$null;error='not found at configured E-drive path'}
    continue
  }
  try {
    $text=(& $cmd @($spec.args) 2>&1 | Out-String).Trim()
    $first=($text -split [Environment]::NewLine | Select-Object -First 1)
    $results += [pscustomobject]@{name=$spec.name;available=$true;command=$cmd;version=$first;error=$null}
  } catch {
    $results += [pscustomobject]@{name=$spec.name;available=$true;command=$cmd;version=$null;error=$_.Exception.Message}
  }
}

$report=[pscustomobject]@{generated_at=(Get-Date).ToString('o');root=$KrishnaRoot;config=$ConfigFile;tools=$results;ready_count=($results|Where-Object {$_.available}).Count;total_count=$results.Count}
$report | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 $OutputPath
$report | ConvertTo-Json -Depth 6
Write-Host "Saved: $OutputPath"