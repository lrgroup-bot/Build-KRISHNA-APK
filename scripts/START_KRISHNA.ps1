param(
    [Parameter(Mandatory=$false)]
    [string]$KrishnaRoot = "E:\Krishna-The GOD",

    [Parameter(Mandatory=$false)]
    [int]$Port = 8766
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$KrishnaRoot = [IO.Path]::GetFullPath($KrishnaRoot)
$coreDir = Join-Path $KrishnaRoot "core"
$logDir = Join-Path $KrishnaRoot "logs"
if (-not (Test-Path -LiteralPath $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
$startLog = Join-Path $logDir "START_KRISHNA.log"
try { Start-Transcript -Path $startLog -Append -Force | Out-Null } catch {}

if (-not (Test-Path -LiteralPath $coreDir)) {
    throw "KRISHNA core directory not found: $coreDir"
}

$env:KRISHNA_HOST = "127.0.0.1"
$env:KRISHNA_PORT = [string]$Port

Write-Host ""
Write-Host "KRISHNA v3 START" -ForegroundColor Cyan
Write-Host "Root : $KrishnaRoot"
Write-Host "Core : $coreDir"
Write-Host "Port : $Port"
Write-Host ""

$desktopExe = Join-Path $KrishnaRoot "KRISHNA.exe"
$consoleExe = Join-Path $KrishnaRoot "KRISHNA-Console.exe"
$desktopPy = Join-Path $coreDir "krishna_desktop.py"
$consolePy = Join-Path $coreDir "krishna_console.py"
$runCorePy = Join-Path $coreDir "run_core.py"

if (Test-Path -LiteralPath $desktopExe) {
    Write-Host "Starting KRISHNA.exe..." -ForegroundColor Green
    Start-Process -FilePath $desktopExe -WorkingDirectory $KrishnaRoot

    $online = $false
    foreach ($i in 1..20) {
        Start-Sleep -Milliseconds 500
        try {
            $status = Invoke-RestMethod -Uri ("http://127.0.0.1:{0}/api/status" -f $Port) -TimeoutSec 2
            if ($status.ok -and $status.core -eq "ONLINE") {
                $online = $true
                Write-Host ("KRISHNA Core: {0}" -f $status.core) -ForegroundColor Green
                break
            }
        } catch {}
    }

    if (-not $online) {
        Write-Warning "KRISHNA.exe launched, but Core status was not confirmed on port $Port."
    }
    Write-Host ("Start log: {0}" -f $startLog)
    Write-Host ""
    Write-Host "Keep this PowerShell window open and send me the output after START_KRISHNA.ps1 runs." -ForegroundColor Yellow
    try { Stop-Transcript | Out-Null } catch {}
    Read-Host "Press Enter only after you have copied/sent the output"
    exit 0
}

if (Test-Path -LiteralPath $consoleExe) {
    Write-Host "Starting KRISHNA-Console.exe..." -ForegroundColor Green
    & $consoleExe
    exit $LASTEXITCODE
}

$venvPython = Join-Path $KrishnaRoot ".venv\Scripts\python.exe"
$pythonPath = $null
if (Test-Path -LiteralPath $venvPython) {
    $pythonPath = $venvPython
} else {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) { $python = Get-Command py -ErrorAction SilentlyContinue }
    if ($python) { $pythonPath = $python.Source }
}
if (-not $pythonPath) {
    throw "Python was not found and no KRISHNA executable is installed."
}
$env:PYTHONPATH = $coreDir

Push-Location $coreDir
try {
    if (Test-Path -LiteralPath $desktopPy) {
        Write-Host "Starting KRISHNA desktop from source..." -ForegroundColor Green
        & $pythonPath $desktopPy
        exit $LASTEXITCODE
    }

    if (Test-Path -LiteralPath $consolePy) {
        Write-Host "Starting KRISHNA console from source..." -ForegroundColor Green
        & $pythonPath $consolePy
        exit $LASTEXITCODE
    }

    if (Test-Path -LiteralPath $runCorePy) {
        Write-Host "Starting KRISHNA Core..." -ForegroundColor Green
        & $pythonPath $runCorePy
        exit $LASTEXITCODE
    }

    throw "No KRISHNA v3 start entrypoint was found under $coreDir"
}
finally {
    Pop-Location
}
