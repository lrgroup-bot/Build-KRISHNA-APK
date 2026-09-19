param([string]$OutputPath = "$env:USERPROFILE\.krishna\mythos-stack-status.json")
$ErrorActionPreference = "Continue"
New-Item -ItemType Directory -Force -Path (Split-Path $OutputPath) | Out-Null
$tools = @(
  @{ name="codebase_memory"; candidates=@("codebase-memory-mcp"); args=@("--version") },
  @{ name="calm"; candidates=@("calm"); args=@("--version") },
  @{ name="mythos_agent"; candidates=@("mythos-agent"); args=@("--version") },
  @{ name="mini_swe"; candidates=@("mini"); args=@("--help") },
  @{ name="swe_rex"; candidates=@("swe-rex"); args=@("--help") },
  @{ name="cua"; candidates=@("cua","cua-driver"); args=@("--help") },
  @{ name="goose"; candidates=@("goose"); args=@("--version") }
)
$results = @()
foreach ($tool in $tools) {
  $found = $null
  foreach ($candidate in $tool.candidates) {
    $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($cmd) { $found = $cmd; break }
  }
  if (-not $found) {
    $results += [pscustomobject]@{name=$tool.name;available=$false;command=$null;version=$null;error="not found on PATH"}
    continue
  }
  try {
    $text = (& $found.Source @($tool.args) 2>&1 | Out-String).Trim()
    $first = ($text -split [Environment]::NewLine | Select-Object -First 1)
    $results += [pscustomobject]@{name=$tool.name;available=$true;command=$found.Source;version=$first;error=$null}
  } catch {
    $results += [pscustomobject]@{name=$tool.name;available=$true;command=$found.Source;version=$null;error=$_.Exception.Message}
  }
}
$arisePath = "$env:USERPROFILE\.krishna\tools\ARISE\.venv\Scripts\python.exe"
if (Test-Path $arisePath) {
  try {
    $v = (& $arisePath -c "import arise; print(getattr(arise,'__version__','installed'))" 2>&1 | Out-String).Trim()
    $results += [pscustomobject]@{name="arise";available=$true;command=$arisePath;version=$v;error=$null}
  } catch {
    $results += [pscustomobject]@{name="arise";available=$true;command=$arisePath;version=$null;error=$_.Exception.Message}
  }
} else { $results += [pscustomobject]@{name="arise";available=$false;command=$null;version=$null;error="isolated ARISE environment not found"} }
$report = [pscustomobject]@{generated_at=(Get-Date).ToString("o");computer=$env:COMPUTERNAME;user=$env:USERNAME;tools=$results;ready_count=($results | Where-Object {$_.available}).Count;total_count=$results.Count}
$report | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 $OutputPath
$report | ConvertTo-Json -Depth 6
Write-Host "Saved: $OutputPath"