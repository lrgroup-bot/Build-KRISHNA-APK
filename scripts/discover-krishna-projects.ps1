param([string[]]$Roots=@(),[int]$MaxDepth=5,[string]$KrishnaRoot="E:\KRISHNA")
$ErrorActionPreference='SilentlyContinue'
$OutputPath=Join-Path $KrishnaRoot 'config\projects.json'
if(-not $Roots -or $Roots.Count -eq 0){
  $Roots=@($KrishnaRoot)
  if(Test-Path 'D:\'){ $Roots += 'D:\' }
}
$Roots=$Roots|Select-Object -Unique
function Get-Depth([string]$root,[string]$path){$base=$root.TrimEnd('\');if($path.Length -le $base.Length){return 0};$rel=$path.Substring($base.Length).Trim('\');if(-not $rel){return 0};return ($rel -split '\\').Count}
$repos=New-Object System.Collections.Generic.List[object]
foreach($root in $Roots){
  if(-not(Test-Path $root)){continue}
  Write-Host "[KRISHNA] Scanning $root for Git projects..." -ForegroundColor Cyan
  Get-ChildItem -LiteralPath $root -Directory -Force -Recurse -ErrorAction SilentlyContinue |
    Where-Object {(Get-Depth $root $_.FullName) -le $MaxDepth -and (Test-Path (Join-Path $_.FullName '.git'))} |
    ForEach-Object {
      $remote=''; try{$remote=(& git -C $_.FullName config --get remote.origin.url 2>$null|Out-String).Trim()}catch{}
      $repos.Add([pscustomobject]@{name=$_.Name;path=$_.FullName;remote=$remote;discovered_at=(Get-Date).ToString('o')})
    }
}
$dedup=$repos|Sort-Object path -Unique
New-Item -ItemType Directory -Force -Path (Split-Path $OutputPath)|Out-Null
[pscustomobject]@{roots=$Roots;count=$dedup.Count;projects=$dedup}|ConvertTo-Json -Depth 6|Set-Content -Encoding UTF8 $OutputPath
Write-Host "[OK] Found $($dedup.Count) Git projects" -ForegroundColor Green
$dedup|Format-Table name,path,remote -AutoSize
Write-Host "Saved: $OutputPath"