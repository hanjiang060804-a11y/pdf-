# pdf-tra 环境初始化（Windows PowerShell）
# 用法：在项目根目录执行  .\scripts\setup.ps1

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $ProjectRoot

Write-Host "==> pdf-tra 环境初始化" -ForegroundColor Cyan
Write-Host "    项目目录: $ProjectRoot"

# pdf2zh 1.9+ 要求 Python >=3.10, <3.13
$PythonCandidates = @("3.12", "3.11", "3.10")
$PythonCmd = $null

foreach ($ver in $PythonCandidates) {
    try {
        $null = & py "-$ver" -c "import sys; print(sys.version)" 2>$null
        if ($LASTEXITCODE -eq 0) {
            $PythonCmd = "py -$ver"
            Write-Host "==> 找到 Python $ver" -ForegroundColor Green
            break
        }
    } catch {
        continue
    }
}

if (-not $PythonCmd) {
    Write-Host ""
    Write-Host "错误: 未找到 Python 3.10~3.12。" -ForegroundColor Red
    Write-Host "当前 pdf2zh 不支持 Python 3.13/3.14。" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "请先安装 Python 3.12:" -ForegroundColor Yellow
    Write-Host "  https://www.python.org/downloads/release/python-3129/" -ForegroundColor Yellow
    Write-Host "安装时勾选 Add python.exe to PATH，然后重新运行本脚本。" -ForegroundColor Yellow
    exit 1
}

$VenvPath = Join-Path $ProjectRoot ".venv"
if (-not (Test-Path $VenvPath)) {
    Write-Host "==> 创建虚拟环境 .venv ..."
    Invoke-Expression "$PythonCmd -m venv `"$VenvPath`""
} else {
    Write-Host "==> 虚拟环境 .venv 已存在，跳过创建"
}

$Activate = Join-Path $VenvPath "Scripts\Activate.ps1"
if (-not (Test-Path $Activate)) {
    Write-Host "错误: 虚拟环境创建失败" -ForegroundColor Red
    exit 1
}

. $Activate

Write-Host "==> Python 版本:"
python --version

Write-Host "==> 升级 pip ..."
python -m pip install -U pip

Write-Host "==> 安装依赖（requirements.txt）..."
Write-Host "    提示: 若官方 PyPI 失败，可开梯子或改用国内镜像" -ForegroundColor DarkGray
pip install -r requirements.txt

if (-not (Test-Path "config.json")) {
    Copy-Item "config.example.json" "config.json"
    Write-Host "==> 已生成 config.json，请编辑填入 DEEPSEEK_API_KEY" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "==> 完成！" -ForegroundColor Green
Write-Host ""
Write-Host "后续每次使用前激活虚拟环境:" -ForegroundColor Cyan
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host ""
Write-Host "验证安装:" -ForegroundColor Cyan
Write-Host "  python -m pdf_tra version"
Write-Host "  pdf2zh --help"
Write-Host "  pytest"
