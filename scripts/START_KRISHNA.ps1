param(
    [Parameter(Mandatory=$false)]
    [string]$KrishnaRoot = "C:\KRISHNA-v3",

    [Parameter(Mandatory=$false)]
    [int]$Port = 8766
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$KrishnaRoot = [IO.Path]::GetFullPath($KrishnaRoot)
$coreDir = Join-Path $KrishnaRoot "core"

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
    exit 0
}

if (Test-Path -LiteralPath $consoleExe) {
    Write-Host "Starting KRISHNA-Console.exe..." -ForegroundColor Green
    & $consoleExe
    exit $LASTEXITCODE
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    $python = Get-Command py -ErrorAction SilentlyContinue
}
if (-not $python) {
    throw "Python was not found and no KRISHNA executable is installed."
}

Push-Location $coreDir
try {
    if (Test-Path -LiteralPath $desktopPy) {
        Write-Host "Starting KRISHNA desktop from source..." -ForegroundColor Green
        & $python.Source $desktopPy
        exit $LASTEXITCODE
    }

    if (Test-Path -LiteralPath $consolePy) {
        Write-Host "Starting KRISHNA console from source..." -ForegroundColor Green
        & $python.Source $consolePy
        exit $LASTEXITCODE
    }

    if (Test-Path -LiteralPath $runCorePy) {
        Write-Host "Starting KRISHNA Core..." -ForegroundColor Green
        & $python.Source $runCorePy
        exit $LASTEXITCODE
    }

    throw "No KRISHNA v3 start entrypoint was found under $coreDir"
}
finally {
    Pop-Location
}
