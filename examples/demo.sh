#!/usr/bin/env bash
# WSLens 一键演示：起服务 → 体检 → 时延 → 收发 → 吞吐 → 关闭
set -euo pipefail

PY="${PYTHON:-python3}"
PORT="${PORT:-8765}"

echo "🛰️  启动内置回显服务器（端口 $PORT）…"
"$PY" -m wslens serve --port "$PORT" --greeting "👋 WSLens 演示服务已就绪" --tick-ms 500 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null || true' EXIT
sleep 1.5

echo ""
echo "🩺 ① 握手与安全体检"
"$PY" -m wslens check "ws://127.0.0.1:$PORT"

echo ""
echo "🏓 ② 时延与抖动"
"$PY" -m wslens ping "ws://127.0.0.1:$PORT" -n 10 -i 0.05

echo ""
echo "📤 ③ 发送消息"
"$PY" -m wslens send "ws://127.0.0.1:$PORT" -m "hello WSLens 🚀" --wait 1.5

echo ""
echo "👂 ④ 监听服务端推送"
"$PY" -m wslens listen "ws://127.0.0.1:$PORT" -d 3 -n 4

echo ""
echo "🚀 ⑤ 吞吐压测"
"$PY" -m wslens bench "ws://127.0.0.1:$PORT" -n 300 -s 1024

echo ""
echo "🎉 演示完成"
