#!/usr/bin/env bash
# CI 发布门禁：WebSocket 端点必须可用、加密、且证书未临期
# 用法: ENDPOINT=wss://api.example.com/ws bash examples/ci_gate.sh
set -uo pipefail

ENDPOINT="${ENDPOINT:?请设置 ENDPOINT 环境变量}"

echo "🔭 体检: $ENDPOINT"
wslens check "$ENDPOINT" --require-tls --json > wslens-report.json
code=$?

if [ $code -ne 0 ]; then
  echo "::error::WebSocket 端点体检未通过（退出码 $code）"
  cat wslens-report.json
  exit $code
fi

echo "🏓 时延抽样"
wslens ping "$ENDPOINT" -n 5 || echo "::warning::PING 未全部成功（服务端可能不实现 PONG）"

echo "✅ WebSocket 端点健康"
