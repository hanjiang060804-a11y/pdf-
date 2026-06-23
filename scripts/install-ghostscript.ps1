# Install Ghostscript (required by ocrmypdf on Windows)
# Usage: .\scripts\install-ghostscript.ps1

$ErrorActionPreference = "Stop"

$Version = "10.00.0"
$ExeName = "gs1000w64.exe"
$GhUrl = "https://github.com/ArtifexSoftware/ghostpdl-downloads/releases/download/gs1000/$ExeName"

$Mirrors = @(
    "https://ghfast.top",
    "https://gh-proxy.com",
    "https://mirror.ghproxy.com"
)

$InstallRoot = Join-Path $env:LOCALAPPDATA "Ghostscript"

function Find-GsBin {
    $roots = @($InstallRoot, "${env:ProgramFiles}\gs")
    foreach ($root in $roots) {
        if (-not (Test-Path $root)) { continue }
        $hit = Get-ChildItem -Path $root -Recurse -Filter "gswin64c.exe" -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($hit) { return $hit }
    }
    return $null
}

function Test-Ghostscript {
    foreach ($name in @("gswin64c", "gswin32c", "gs")) {
        if (Get-Command $name -ErrorAction SilentlyContinue) {
            return $name
        }
    }
    return $null
}

$existing = Test-Ghostscript
if ($existing) {
    $ver = & $existing --version 2>&1 | Select-Object -First 1
    Write-Host "==> Ghostscript already on PATH: $ver" -ForegroundColor Green
    exit 0
}

$gsExe = Find-GsBin
if ($gsExe) {
    $binDir = $gsExe.DirectoryName
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($userPath -notlike "*$binDir*") {
        [Environment]::SetEnvironmentVariable("Path", ($userPath + ";" + $binDir), "User")
    }
    $env:Path = $env:Path + ";" + $binDir
    Write-Host "==> Added Ghostscript to PATH: $binDir" -ForegroundColor Green
    exit 0
}

$ExePath = Join-Path $env:TEMP $ExeName
$Downloaded = $false

foreach ($mirror in $Mirrors) {
    $Url = "$mirror/$GhUrl"
    Write-Host "==> Mirror: $mirror" -ForegroundColor Cyan
    try {
        curl.exe -L -f -o $ExePath $Url
        if ((Test-Path $ExePath) -and (Get-Item $ExePath).Length -gt 5MB) {
            $Downloaded = $true
            Write-Host "==> Download OK" -ForegroundColor Green
            break
        }
    } catch {
        Write-Host "    failed, try next..." -ForegroundColor DarkGray
    }
    Remove-Item $ExePath -Force -ErrorAction SilentlyContinue
}

if (-not $Downloaded) {
    Write-Host "ERROR: download failed. Install manually from:" -ForegroundColor Red
    Write-Host "  https://ghostscript.com/releases/gsdnld.html"
    exit 1
}

if (Test-Path $InstallRoot) {
    Remove-Item $InstallRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $InstallRoot -Force | Out-Null

Write-Host "==> Installing to $InstallRoot ..."
$proc = Start-Process -FilePath $ExePath -ArgumentList @("/S", "/D=$InstallRoot") -Wait -PassThru
Remove-Item $ExePath -Force -ErrorAction SilentlyContinue

if ($proc.ExitCode -ne 0) {
    Write-Host "WARN: installer exit $($proc.ExitCode), searching gswin64c..." -ForegroundColor Yellow
}

$gsExe = Find-GsBin
if (-not $gsExe) {
    $gsExe = Get-ChildItem -Path $env:ProgramFiles -Recurse -Filter "gswin64c.exe" -ErrorAction SilentlyContinue |
        Select-Object -First 1
}
if (-not $gsExe) {
    Write-Host "ERROR: gswin64c.exe not found after install" -ForegroundColor Red
    exit 1
}

$BinDir = $gsExe.DirectoryName
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$BinDir*") {
    [Environment]::SetEnvironmentVariable("Path", ($userPath + ";" + $BinDir), "User")
    Write-Host "==> Added to user PATH: $BinDir" -ForegroundColor Green
}
$env:Path = $env:Path + ";" + $BinDir

$ver = & gswin64c --version 2>&1 | Select-Object -First 1
Write-Host "==> OK: $ver" -ForegroundColor Green
Write-Host "    Restart pdf_tra web server, then retry scanned PDF OCR."
