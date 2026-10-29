# WSLens 一键构建脚本（Windows / PowerShell）
#
# 产物输出到 dist\：
#   1. wheel  —— 若环境已安装 build / pip wheel 则生成
#   2. wslens.pyz —— 一定生成的单文件可执行归档（zipapp）
#
# 用法:  powershell -ExecutionPolicy Bypass -File scripts\build.ps1

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Python = if ($env:PYTHON) { $env:PYTHON } else { "python" }
$Dist = Join-Path $Root "dist"

Write-Host "🧹 清理旧产物…"
if (Test-Path $Dist) { Remove-Item -Recurse -Force $Dist }
if (Test-Path (Join-Path $Root "build")) { Remove-Item -Recurse -Force (Join-Path $Root "build") }
Get-ChildItem -Path $Root -Filter "*.egg-info" -Directory -ErrorAction SilentlyContinue |
  ForEach-Object { Remove-Item -Recurse -Force $_.FullName }
New-Item -ItemType Directory -Path $Dist | Out-Null

Write-Host "🧪 运行测试…"
& $Python "tests/run.py"
if ($LASTEXITCODE -ne 0) { throw "测试未通过，已中止构建" }

Write-Host "📦 构建 wheel…"
$built = $false
try {
  & $Python -m build --wheel --sdist --outdir $Dist
  if ($LASTEXITCODE -eq 0) { $built = $true }
} catch { $built = $false }
if (-not $built) {
  Write-Host "   ⚠️  未检测到 build 模块，改用 pip wheel 回退方案"
  try {
    & $Python -m pip wheel . --no-deps -w $Dist
    if ($LASTEXITCODE -eq 0) { $built = $true }
  } catch { $built = $false }
}
if (-not $built) { Write-Host "   ⚠️  已跳过 wheel 构建（不影响 pyz 产物）" }

Write-Host "🗜️  构建单文件可执行归档 wslens.pyz…"
$Stage = Join-Path $Dist "_stage"
New-Item -ItemType Directory -Path (Join-Path $Stage "wslens") -Force | Out-Null
Copy-Item -Path (Join-Path $Root "wslens\*.py") -Destination (Join-Path $Stage "wslens") -Force
& $Python -m zipapp $Stage --main "wslens.__main__:main" --output "$Dist/wslens.pyz" --compress
if ($LASTEXITCODE -ne 0) { throw "zipapp 构建失败" }
Remove-Item -Recurse -Force $Stage
if ($LASTEXITCODE -ne 0) { throw "zipapp 构建失败" }

Write-Host "🔍 冒烟验证…"
& $Python "$Dist/wslens.pyz" selftest

Write-Host ""
Write-Host "🎉 构建完成，产物位于 $Dist"
Get-ChildItem $Dist | ForEach-Object { Write-Host ("   {0}" -f $_.Name) }
Write-Host ""
Write-Host "运行方式："
Write-Host "  python $Dist\wslens.pyz check wss://ws.postman-echo.com/raw"
