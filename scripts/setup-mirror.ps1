# 使用国内镜像安装（PyPI 官方 SSL 失败时使用）
# 用法：先运行 setup.ps1 创建 .venv，再执行本脚本；或手动激活 .venv 后运行

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $ProjectRoot

$Mirror = "https://pypi.tuna.tsinghua.edu.cn/simple"
$TrustedHost = "pypi.tuna.tsinghua.edu.cn"

$Activate = Join-Path $ProjectRoot ".venv\Scripts\Activate.ps1"
if (-not (Test-Path $Activate)) {
    Write-Host "请先运行 .\scripts\setup.ps1 创建虚拟环境" -ForegroundColor Red
    exit 1
}

. $Activate

Write-Host "==> 使用清华镜像安装依赖 ..." -ForegroundColor Cyan
python -m pip install -U pip -i $Mirror --trusted-host $TrustedHost
pip install -r requirements.txt -i $Mirror --trusted-host $TrustedHost

Write-Host "==> 完成" -ForegroundColor Green
