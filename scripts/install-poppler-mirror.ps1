# 从 GitHub 国内镜像下载并安装 Poppler（Windows）
# 用法：.\scripts\install-poppler-mirror.ps1

$ErrorActionPreference = "Stop"

$Version = "25.07.0-0"
$ZipName = "Release-$Version.zip"
$GhUrl = "https://github.com/oschwartz10612/poppler-windows/releases/download/v$Version/$ZipName"

# GitHub 国内镜像（按顺序尝试）
$Mirrors = @(
    "https://ghfast.top",
    "https://gh-proxy.com",
    "https://mirror.ghproxy.com"
)

$InstallRoot = Join-Path $env:LOCALAPPDATA "poppler"
$BinDir = $null

function Test-Poppler {
    $pdfinfo = Get-Command pdfinfo -ErrorAction SilentlyContinue
    return $null -ne $pdfinfo
}

if (Test-Poppler) {
    Write-Host "==> poppler 已在 PATH 中: $(pdfinfo -v 2>&1 | Select-Object -First 1)" -ForegroundColor Green
    exit 0
}

$ZipPath = Join-Path $env:TEMP $ZipName
$Downloaded = $false

foreach ($mirror in $Mirrors) {
    $Url = "$mirror/$GhUrl"
    Write-Host "==> 尝试镜像: $mirror" -ForegroundColor Cyan
    try {
        curl.exe -L -f -o $ZipPath $Url
        if ((Test-Path $ZipPath) -and (Get-Item $ZipPath).Length -gt 1MB) {
            $Downloaded = $true
            Write-Host "==> 下载成功" -ForegroundColor Green
            break
        }
    } catch {
        Write-Host "    失败，换下一个镜像..." -ForegroundColor DarkGray
    }
    Remove-Item $ZipPath -Force -ErrorAction SilentlyContinue
}

if (-not $Downloaded) {
    Write-Host "错误: 所有镜像均下载失败，请开 VPN 后重试或手动下载:" -ForegroundColor Red
    Write-Host "  $GhUrl"
    exit 1
}

if (Test-Path $InstallRoot) {
    Remove-Item $InstallRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $InstallRoot -Force | Out-Null

Write-Host "==> 解压到 $InstallRoot ..."
Expand-Archive -Path $ZipPath -DestinationPath $InstallRoot -Force
Remove-Item $ZipPath -Force

$PdfInfo = Get-ChildItem -Path $InstallRoot -Recurse -Filter "pdfinfo.exe" -ErrorAction SilentlyContinue |
    Select-Object -First 1
if (-not $PdfInfo) {
    Write-Host "错误: 解压后未找到 pdfinfo.exe" -ForegroundColor Red
    exit 1
}
$BinDir = $PdfInfo.DirectoryName

# 加入用户 PATH（永久）
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$BinDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$BinDir", "User")
    Write-Host "==> 已加入用户 PATH: $BinDir" -ForegroundColor Green
} else {
    Write-Host "==> PATH 中已包含 poppler" -ForegroundColor DarkGray
}

$env:Path = "$env:Path;$BinDir"
$ver = & pdfinfo -v 2>&1 | Select-Object -First 1
Write-Host "==> 验证: $ver" -ForegroundColor Green
Write-Host "    新开终端后 pdfinfo / pdftotext 全局可用"
