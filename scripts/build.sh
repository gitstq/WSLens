#!/usr/bin/env bash
# WSLens 一键构建脚本（Linux / macOS / WSL）
#
# 产物输出到 dist/：
#   1. wheel  —— 若环境已安装 build / pip wheel 则生成
#   2. wslens.pyz —— 一定生成的单文件可执行归档（zipapp），
#      `python dist/wslens.pyz --help` 即可运行，零依赖、跨平台
#
# 用法:  bash scripts/build.sh

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"
DIST="$ROOT/dist"

echo "🧹 清理旧产物…"
rm -rf "$DIST" "$ROOT/build" "$ROOT"/*.egg-info
mkdir -p "$DIST"

echo "🧪 运行测试…"
"$PYTHON" tests/run.py

echo "📦 构建 wheel…"
if "$PYTHON" -m build --wheel --sdist --outdir "$DIST" 2>/dev/null; then
  echo "   ✅ wheel / sdist 已生成"
else
  echo "   ⚠️  未检测到 build 模块，改用 pip wheel 回退方案"
  if "$PYTHON" -m pip wheel . --no-deps -w "$DIST" 2>/dev/null; then
    echo "   ✅ wheel 已生成"
  else
    echo "   ⚠️  pip wheel 不可用，跳过 wheel 构建（不影响 pyz 产物）"
  fi
fi

echo "🗜️  构建单文件可执行归档 wslens.pyz…"
STAGE="$DIST/_stage"
mkdir -p "$STAGE/wslens"
cp "$ROOT"/wslens/*.py "$STAGE/wslens/"
"$PYTHON" -m zipapp "$STAGE" \
  --main "wslens.__main__:main" \
  --python "/usr/bin/env python3" \
  --output "$DIST/wslens.pyz" \
  --compress
rm -rf "$STAGE"
chmod +x "$DIST/wslens.pyz"

echo "🔍 冒烟验证…"
"$PYTHON" "$DIST/wslens.pyz" selftest

echo ""
echo "🎉 构建完成，产物位于 $DIST:"
ls -lh "$DIST"
echo ""
echo "运行方式："
echo "  python $DIST/wslens.pyz check wss://ws.postman-echo.com/raw"
