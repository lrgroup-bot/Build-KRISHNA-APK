param(
    [Parameter(Mandatory=$false)]
    [string]$PackageRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,

    [Parameter(Mandatory=$false)]
    [string]$TargetRoot = "C:\KRISHNA-v3"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Write-Step([string]$Message) {
    Write-Host "[KRISHNA PATCH] $Message" -ForegroundColor Cyan
}

function Ensure-Directory([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
        Write-Step "Created directory: $Path"
    }
}

$PackageRoot = [IO.Path]::GetFullPath($PackageRoot)
$TargetRoot = [IO.Path]::GetFullPath($TargetRoot)

if (-not (Test-Path -LiteralPath $PackageRoot)) {
    throw "PackageRoot does not exist: $PackageRoot"
}

Write-Step "Package: $PackageRoot"
Write-Step "Target : $TargetRoot"
Ensure-Directory $TargetRoot

# These paths are NEVER overwritten or deleted by this patch.
$ProtectedRelative = @(
    "krishna.glb",
    "core\krishna.py",
    "gateway",
    "mobile_gateway",
    "certificates",
    "certs",
    "credentials",
    "device_credentials",
    "ollama",
    "models",
    "state",
    "data",
    "memory",
    "krishna_core.db",
    ".env"
)

function Is-Protected([string]$RelativePath) {
    $normalized = $RelativePath.Replace("/", "\").TrimStart("\")
    foreach ($protected in $ProtectedRelative) {
        if ($normalized -ieq $protected -or $normalized.StartsWith($protected + "\", [System.StringComparison]::OrdinalIgnoreCase)) {
            return $true
        }
    }
    return $false
}

# Only these v3 runtime locations are eligible for installation.
$RuntimeSources = @(
    @{ Source = "core\krishna_core"; Destination = "core\krishna_core" },
    @{ Source = "core\dashboard.html"; Destination = "core\dashboard.html" },
    @{ Source = "core\krishna_console.py"; Destination = "core\krishna_console.py" },
    @{ Source = "core\krishna_desktop.py"; Destination = "core\krishna_desktop.py" },
    @{ Source = "core\.env.example"; Destination = "core\.env.example" }
)

$installed = New-Object System.Collections.Generic.List[string]
$preserved = New-Object System.Collections.Generic.List[string]
$missingPackage = New-Object System.Collections.Generic.List[string]

function Copy-MissingFile([string]$SourceFile, [string]$DestinationFile, [string]$RelativeDestination) {
    if (Is-Protected $RelativeDestination) {
        $preserved.Add($RelativeDestination)
        return
    }

    if (Test-Path -LiteralPath $DestinationFile) {
        $preserved.Add($RelativeDestination)
        return
    }

    Ensure-Directory (Split-Path -Parent $DestinationFile)
    Copy-Item -LiteralPath $SourceFile -Destination $DestinationFile
    $installed.Add($RelativeDestination)
}

foreach ($entry in $RuntimeSources) {
    $source = Join-Path $PackageRoot $entry.Source
    $destination = Join-Path $TargetRoot $entry.Destination

    if (-not (Test-Path -LiteralPath $source)) {
        $missingPackage.Add($entry.Source)
        continue
    }

    $item = Get-Item -LiteralPath $source
    if ($item.PSIsContainer) {
        Get-ChildItem -LiteralPath $source -File -Recurse | ForEach-Object {
            $relativeInside = $_.FullName.Substring($source.Length).TrimStart("\", "/")
            $relativeDestination = Join-Path $entry.Destination $relativeInside
            $destinationFile = Join-Path $TargetRoot $relativeDestination
            Copy-MissingFile $_.FullName $destinationFile $relativeDestination
        }
    } else {
        Copy-MissingFile $source $destination $entry.Destination
    }
}

Write-Host ""
Write-Step "Installed missing runtime files: $($installed.Count)"
$installed | ForEach-Object { Write-Host "  + $_" -ForegroundColor Green }

Write-Step "Preserved existing/protected files: $($preserved.Count)"
$preserved | ForEach-Object { Write-Host "  = $_" -ForegroundColor DarkGray }

if ($missingPackage.Count -gt 0) {
    Write-Host ""
    Write-Warning "Some optional runtime sources were not present in the package:"
    $missingPackage | ForEach-Object { Write-Host "  ! $_" -ForegroundColor Yellow }
}

Write-Host ""
Write-Host "PRESERVATION GUARANTEE" -ForegroundColor Yellow
Write-Host "This patch installs only missing v3 Core/dashboard runtime files."
Write-Host "It does NOT overwrite or delete krishna.glb, existing core\krishna.py,"
Write-Host "mobile gateway/certificates/device credentials, Ollama models, state data,"
Write-Host "memory/database files, or .env."
Write-Host ""
Write-Host "Patch complete." -ForegroundColor Green
