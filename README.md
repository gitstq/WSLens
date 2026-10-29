<div align="center">

# 🔭 WSLens

**零依赖 · 离线优先的 WebSocket 诊断与性能探针**

[简体中文](./README.zh-CN.md) · [繁體中文](./README.zh-TW.md) · [English](./README.en.md)

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Dependencies](https://img.shields.io/badge/dependencies-0-brightgreen)](#-核心特性)
[![License](https://img.shields.io/badge/license-MIT-green)](#-开源协议说明)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)](#-打包与部署指南)

</div>

---

## 🎉 项目介绍

WebSocket 上线后"能连上但不好用"的问题，往往最难定位：握手是不是真的 101？证书还有几天过期？PING/PONG 到底多少毫秒？有没有丢包？——这些问题通常要装 `wscat`、配 Node 环境、或者打开浏览器 DevTools 才能回答。

**WSLens** 把这套诊断能力收敛进一个 **零第三方依赖、纯 Python 标准库** 的命令行工具里。它自带一份完整的 RFC 6455 实现（帧编解码 + 握手 + 心跳），因此**不需要 `websockets`、`websocket-client` 或任何 pip 包**，也不需要 Node.js。复制一个文件就能在没有外网的机器上跑起来。

### 🎯 解决什么痛点

| 痛点 | 过去怎么做 | WSLens 怎么做 |
| --- | --- | --- |
| 🤔 连不上，不知道卡在哪一步 | 抓包 / 翻日志 | `wslens check` 直接告诉你握手码、Accept 校验、TLS 版本 |
| 🐢 怀疑链路慢，但没有数据 | 写脚本或装 Node 工具 | `wslens ping` 给出 min/avg/P95/max/抖动/丢包 |
| 🔐 证书什么时候过期 | `openssl s_client` 拼命令 | `check` 直接算出剩余天数并告警 |
| 📉 想知道吞吐上限 | 找压测平台 | `wslens bench` 本地一条命令出 msg/s 与 MiB/s |
| 🧪 CI 里想做连通性门禁 | 没有合适工具 | `--json` + 明确的退出码，天然适配流水线 |
| 📦 内网机器装不了依赖 | 放弃 / 手动编译 | 0 依赖，`wslens.pyz` 单文件拷进去就能跑 |

### 💎 自研差异化亮点

- 🧬 **协议栈自己实现**：RFC 6455 帧编解码、掩码、`Sec-WebSocket-Accept` 校验全部自研，不依赖任何第三方协议库，行为完全可控可审计。
- 🛰️ **内置回显服务器**：自带一个零依赖 WebSocket 服务端，`wslens selftest` 可在**完全离线**的环境下完成端到端自测——这是绝大多数同类 CLI 不具备的能力。
- 📊 **面向诊断而非仅仅收发**：不止"发个消息"，而是给出统计口径完整的时延分布（P95 / 抖动 / 丢包率）与 Unicode 走势图。
- 🤖 **CI 友好**：所有子命令支持 `--json`，退出码语义明确，可直接作为发布门禁。
- 🪶 **单文件分发**：除 wheel 外，构建脚本额外产出 `wslens.pyz`（zipapp 单文件可执行归档），`python wslens.pyz` 即用。

---

## ✨ 核心特性

### 🔍 协议与连接
- ✅ 完整 **RFC 6455** 数据帧编解码：7 / 16 / 64 位长度扩展、分片续帧、客户端掩码
- ✅ 握手校验：**101 状态码**、`Sec-WebSocket-Accept` 本地重算比对、`Upgrade`/`Connection` 头检查
- ✅ 支持 `ws://` 与 `wss://`（TLS），可读取 **TLS 版本、加密套件、证书 CN/签发机构/剩余天数**
- ✅ 自定义请求头（`-H`）、`Origin`、User-Agent、**子协议协商**（`--subprotocol`）
- ✅ 控制帧自动处理：收到服务端 PING 自动回 PONG；关闭帧解析出 code 与 reason

### 📈 测量能力
- 🏓 `ping` —— 多次 PING/PONG，输出 **min / avg / P95 / max / 标准差 / 抖动 / 丢包率** 与走势图
- 🚀 `bench` —— 吞吐压测，输出 **msg/s、MiB/s、平均往返、P95 往返、失败数**
- 📤 `send` —— 发送文本或二进制（含从文件读取），打印回显，支持 `--expect` 断言
- 👂 `listen` —— 持续监听服务端推送，可限时、限条数、打印十六进制
- 🩺 `check` —— 一次输出 **6 项体检结论**：握手码 / Accept / Upgrade 头 / 子协议 / TLS 版本 / 证书有效期

### 🛠️ 工程化
- 🧪 `selftest` —— 离线端到端自测（7 项：握手、文本、二进制、64 位长度、心跳、吞吐、关闭）
- 🛰️ `serve` —— 内置回显服务器，支持人为延迟、前缀、大写转换、欢迎语、定时推送（模拟弱网与推送场景）
- 📦 一键构建：`wheel` + `wslens.pyz` 单文件产物，Windows / macOS / Linux 通吃
- 🧩 44 项单元测试，`python tests/run.py` 直接跑（不需要 pytest）
- 🎨 人类可读彩色输出 + `--json` 机读输出双模，`--no-color` 可关闭颜色

---

## 🚀 快速开始

### 📋 环境要求

| 项目 | 要求 |
| --- | --- |
| Python | **3.8 及以上**（实测 3.11） |
| 操作系统 | Windows / macOS / Linux 任意 |
| 第三方依赖 | **无**（仅使用 Python 标准库） |
| 网络 | 诊断公网端点时需要；`selftest` 完全离线 |

### ⚡ 三种安装方式（任选其一）

**方式一：pip 安装（推荐）**

```bash
pip install wslens
wslens --version
```

**方式二：免安装，单文件运行**

```bash
# 从 Releases 拿到 wslens.pyz 后，或本地构建：
python wslens.pyz --help
```

**方式三：从源码直接跑（零安装）**

```bash
git clone https://github.com/gitstq/WSLens.git
cd WSLens
python -m wslens --help          # 不安装任何东西，立即可用
```

### 🏁 30 秒上手

```bash
# ① 先离线自测，确认环境没问题
python -m wslens selftest

# ② 起一个本地回显服务器（另开一个终端）
python -m wslens serve --port 8765 --greeting "👋 你好" --tick-ms 1000

# ③ 体检
python -m wslens check ws://127.0.0.1:8765

# ④ 测时延
python -m wslens ping ws://127.0.0.1:8765 -n 10

# ⑤ 发消息
python -m wslens send ws://127.0.0.1:8765 -m "hello wslens" --wait 2

# ⑥ 压吞吐
python -m wslens bench ws://127.0.0.1:8765 -n 500 -s 1024
```

### 🧪 对着公网真实端点试

```bash
python -m wslens check wss://ws.postman-echo.com/raw
python -m wslens ping  wss://echo.websocket.org -n 10
```

---

## 📖 详细使用指南

### 🧭 命令总览

| 命令 | 作用 | 常用参数 |
| --- | --- | --- |
| `check` | 🩺 握手与安全体检 | `--require-tls` |
| `ping` | 🏓 PING/PONG 时延统计 | `-n/--count`、`-i/--interval` |
| `send` | 📤 发送并打印回显 | `-m/--message`、`--file`、`--binary`、`--wait`、`--expect` |
| `listen` | 👂 监听服务端推送 | `-d/--duration`、`-n/--max-messages`、`--show-bytes` |
| `bench` | 🚀 吞吐与时延压测 | `-n/--count`、`-s/--size`、`--binary` |
| `serve` | 🛰️ 启动内置回显服务器 | `-p/--port`、`--delay-ms`、`--prefix`、`--upper`、`--greeting`、`--tick-ms` |
| `selftest` | 🧪 离线端到端自测 | — |

### 🌐 全局参数（可放在子命令之前或之后）

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `--json` | 关 | 以 JSON 输出，便于管道与 CI 消费 |
| `-t, --timeout` | `10` | 超时秒数 |
| `--insecure` | 关 | 跳过 TLS 证书校验（**仅调试用**） |
| `--max-payload` | `33554432` | 单帧负载上限（字节），防内存打爆 |
| `-H, --header` | — | 附加请求头，格式 `Name: value`，可重复 |
| `--origin` | 自动 | 覆盖 `Origin` 请求头 |
| `--subprotocol` | — | 请求的子协议，可重复指定 |
| `--user-agent` | `WSLens/1.0.0` | 自定义 User-Agent |
| `--no-color` | 关 | 关闭彩色输出 |

---

### 🩺 `check` —— 握手与安全体检

```bash
wslens check wss://ws.postman-echo.com/raw
```

真实输出示例：

```
🎯 目标  wss://ws.postman-echo.com/raw
────────────────────────────────────────────────────────
  握手状态              HTTP 101 Switching Protocols
  握手耗时              973.6 ms
  服务端标识             nginx
  TLS 版本            TLSv1.2
  加密套件              ECDHE-RSA-AES128-GCM-SHA256 (128 bits)
  证书 CN             postman-echo.com
  签发机构              Amazon
  剩余有效期             121 天 (2027-02-28T07:59:59+08:00)

🩺 体检结果
────────────────────────────────────────────────────────
  ✅ 握手状态码                   HTTP 101 Switching Protocols
  ✅ Sec-WebSocket-Accept 校验 与 RFC 6455 期望值一致
  ✅ Upgrade / Connection 头  Upgrade=websocket Connection=upgrade
  ⏭️ 子协议协商                   未请求或未协商子协议
  ✅ TLS 版本                  TLSv1.2 · ECDHE-RSA-AES128-GCM-SHA256 (128 bits)
  ✅ 证书有效期                   剩余 121 天 · CN=postman-echo.com
  综合结论              ✅ 通过
```

判定口径：

- ✅ **通过** —— 全部检查项正常
- ⚠️ **告警** —— 例如使用明文 `ws://`、证书剩余不足 14 天、TLS 低于 1.2
- ❌ **失败** —— 非 101、Accept 校验不匹配、证书已过期；加 `--require-tls` 时明文连接也判失败

> 💡 明文 `ws://` 默认只告警不失败，方便本地调试；生产门禁请加 `--require-tls`。

---

### 🏓 `ping` —— 时延与抖动

```bash
wslens ping ws://127.0.0.1:8765 -n 10 -i 0.1
```

```
🏓 PING  ws://127.0.0.1:8765
────────────────────────────────────────────────────────
  发送 / 接收           10 / 10  (丢包 0.0%)
  最小 / 平均           0.07 ms / 0.31 ms
  P95 / 最大          1.84 ms / 1.84 ms
  抖动 / 标准差          0.27 ms / 0.58 ms
  RTT 走势            ▁▁▁▁▁▁▁█ (0.1–1.8 ms)
```

指标含义：

| 指标 | 含义 | 怎么读 |
| --- | --- | --- |
| `min / avg / max` | 最小 / 平均 / 最大往返时延 | avg 是主要参考值 |
| `P95` | 95 分位时延 | **比 avg 更能反映长尾用户的真实体验** |
| `抖动 jitter` | 相邻 RTT 差值的平均绝对值 | 越大说明链路越不稳定 |
| `丢包率` | 未收到 PONG 的比例 | 非 0 就要警惕连接质量 |

---

### 🚀 `bench` —— 吞吐压测

```bash
wslens bench ws://127.0.0.1:8765 -n 300 -s 2048
```

```
🚀 吞吐压测  ws://127.0.0.1:8765
────────────────────────────────────────────────────────
  消息条数              300 条 × 2048 字节
  总耗时               0.005 s
  吞吐                57552.9 msg/s · 112.408 MiB/s
  平均往返              0.02 ms
  P95 往返            0.02 ms
  失败条数              0
```

> ⚠️ 这是**串行往返**压测（发一条、等回显、再发下一条），测的是"单连接的请求-响应能力"，**不是**并发极限吞吐。用于对比不同环境 / 不同服务端的相对差异最合适。

---

### 📤 `send` —— 发送并断言

```bash
# 发送文本
wslens send ws://127.0.0.1:8765 -m "hello" --wait 2

# 发送二进制（从文件）
wslens send ws://127.0.0.1:8765 --file ./payload.bin --binary --wait 3

# CI 断言：必须至少收到 1 条回显，否则退出码非 0
wslens send wss://example.com/ws -m "ping" --expect 1 --wait 5
```

---

### 👂 `listen` —— 监听服务端推送

```bash
# 监听 30 秒
wslens listen wss://example.com/feed -d 30

# 只取前 5 条，二进制按十六进制打印
wslens listen wss://example.com/feed -n 5 --show-bytes
```

配合内置服务器体验推送场景：

```bash
wslens serve --port 8765 --greeting "👋 已连接" --tick-ms 500
wslens listen ws://127.0.0.1:8765 -d 5
```

---

### 🛰️ `serve` —— 内置回显服务器

不只是一个测试桩，它可以当作真实的本地调试服务：

```bash
# 基础回显
wslens serve --port 8765

# 模拟弱网（每条消息延迟 200ms）
wslens serve --port 8765 --delay-ms 200

# 模拟服务端定时推送
wslens serve --port 8765 --tick-ms 500 --greeting "👋 welcome"

# 回显时加前缀 / 转大写，便于区分消息来源
wslens serve --port 8765 --prefix "[echo] " --upper
```

---

### 🧪 `selftest` —— 离线端到端自测

```bash
wslens selftest
```

```
🧪 WSLens 离线自测
────────────────────────────────────────────────────────
  ✅ 握手 101 + Accept 校验          HTTP 101 · 1.3 ms
  ✅ 文本消息往返                      hello wslens
  ✅ 二进制消息往返                     256 字节
  ✅ 64 位长度扩展                    70000 字节
  ✅ PING/PONG 心跳                avg 0.09 ms
  ✅ 吞吐压测                        29559.14 msg/s
  ✅ 正常关闭                        code=1000

  📊 结果: 7/7 项通过
```

> 它会自动拉起内置回显服务器，跑完全套链路后再关闭，**全程不访问外网**。装完先跑这个，能一次排除环境、权限、端口等问题。

---

### 🔁 退出码（CI 门禁用）

| 退出码 | 含义 | 典型场景 |
| --- | --- | --- |
| `0` | ✅ 成功 | 全部正常 |
| `1` | ❌ 通用错误 | 参数错误、压测中出现失败条目 |
| `2` | 🔌 连接失败 | DNS 解析失败、端口不通、TLS 握手失败 |
| `3` | 🤝 握手/协议失败 | 非 101 响应、Accept 校验失败 |
| `4` | ⏱️ 超时 | 握手超时、未收到期望条数的消息 |
| `5` | 🩺 体检未通过 | `check` 中存在 ❌ 项 |

### 🤖 CI 集成示例

```bash
#!/usr/bin/env bash
set -euo pipefail

# 发布后门禁：WebSocket 端点必须可用且证书未临期
wslens check "wss://api.example.com/ws" --require-tls --json > report.json
code=$?

if [ $code -ne 0 ]; then
  echo "::error::WebSocket 端点体检未通过（退出码 $code）"
  cat report.json
  exit $code
fi

echo "✅ WebSocket 端点健康"
```

GitHub Actions 片段：

```yaml
- name: 🔭 WebSocket 健康门禁
  run: |
    pip install wslens
    wslens check "${{ secrets.WS_ENDPOINT }}" --require-tls
    wslens ping  "${{ secrets.WS_ENDPOINT }}" -n 5
```

---

### 🐍 作为 Python 库使用

```python
from wslens.client import WSClient, ConnectOptions

with WSClient("wss://ws.postman-echo.com/raw", ConnectOptions(timeout=8)) as ws:
    print(ws.handshake.status_code)      # 101
    print(ws.handshake.elapsed_ms)       # 握手耗时
    ws.send_text("hello")
    print(ws.recv_message(timeout=5).text)
    print(ws.ping())                     # 往返时延（毫秒）
```

---

## 💡 设计思路与迭代规划

### 🏗️ 架构与模块划分

```
wslens/
├── frame.py       # RFC 6455 帧编解码：掩码、长度扩展、分片组装
├── handshake.py   # URL 解析、Upgrade 请求构造、101 响应校验、证书信息提取
├── client.py      # 连接生命周期：建连、收发、心跳、关闭
├── measure.py     # 时延/吞吐统计与体检规则
├── echod.py       # 内置零依赖回显服务器（离线自测与本地联调）
├── report.py      # 终端渲染（文本 / JSON）
└── cli.py         # 命令行入口与子命令编排
```

分层原则：**协议层（frame/handshake）不感知业务，业务层（measure/report）不碰 socket**。这样每一层都能被单独测试——44 项单元测试正是按这个边界组织的。

### 🤔 关键技术选型

| 决策 | 选择 | 原因 |
| --- | --- | --- |
| 语言 | **Python 标准库** | 跨平台一致、无需编译；`socket`/`ssl`/`struct`/`hashlib` 已足够实现 RFC 6455 |
| 第三方依赖 | **0 个** | 内网、离线、审计友好；`pip install` 永不失败 |
| 并发模型 | **同步阻塞 IO** | 诊断场景是"一问一答"，同步模型代码量小、时序测量更精确 |
| 测试框架 | **unittest** | 标准库自带，保证"零依赖"承诺连测试环节也不破例 |
| 分发形态 | **wheel + pyz** | wheel 走常规安装；pyz 单文件满足拷进内网即用的场景 |
| 掩码实现 | **大整数异或** | 避免逐字节 Python 循环，大负载下编码开销显著降低 |

### 🛣️ 后续迭代规划

- [ ] 🌐 HTTP/1.1 代理（CONNECT）与 `HTTPS_PROXY` 支持
- [ ] 🍪 握手阶段的 Cookie / 自定义鉴权头模板（如 Bearer Token 快捷参数）
- [ ] 📉 `ping` 支持长时间运行并输出分位数直方图（P50/P90/P99）
- [ ] 🔁 自动重连与断线次数统计（`--reconnect`）
- [ ] 🧵 `bench` 增加并发连接数维度（`-c/--connections`）
- [ ] 📤 支持导出 HAR / CSV 报告，便于做趋势对比
- [ ] 🧩 提供 MCP 服务器形态，供 AI Agent 直接调用诊断能力
- [ ] 🧪 增加对 permessage-deflate 扩展的探测

### 🙌 社区贡献方向

- 补充更多真实服务端（如各类网关、云厂商 WS 网关）的兼容性用例
- 完善非 UTF-8、异常分片等边界场景的模糊测试
- 翻译更多语言版本的 README（日语 / 韩语 / 西班牙语等）

---

## 📦 打包与部署指南

本项目属于 **CLI 工具类**，无需打包成桌面可执行程序，提供 wheel 与单文件归档两种形态。

### 🛠️ 一键构建

```bash
# Linux / macOS / WSL
bash scripts/build.sh

# Windows（PowerShell）
powershell -ExecutionPolicy Bypass -File scripts\build.ps1

# 或者用 Makefile
make build
```

构建流程会自动完成：**清理 → 跑测试 → 构建 wheel/sdist → 生成 `wslens.pyz` → 冒烟验证**。

产物位于 `dist/`：

```
dist/
├── wslens-1.0.0-py3-none-any.whl   # 标准 wheel，pip install 用
└── wslens.pyz                      # 单文件可执行归档（zipapp）
```

### 🚚 部署方式

**① 常规安装**

```bash
pip install dist/wslens-1.0.0-py3-none-any.whl
wslens --version
```

**② 单文件拷进内网机器（无需安装、无需联网）**

```bash
# 目标机器只要有 Python 3.8+
python wslens.pyz check ws://10.0.0.5:8765
python wslens.pyz selftest
```

**③ 源码部署**

```bash
git clone https://github.com/gitstq/WSLens.git
cd WSLens
python -m wslens selftest      # 无需 pip install
```

### ✅ 兼容性矩阵

| 环境 | 状态 | 说明 |
| --- | --- | --- |
| Linux (x86_64 / ARM) | ✅ 支持 | 已实测 Ubuntu 22.04 |
| macOS (Intel / Apple Silicon) | ✅ 支持 | 标准库实现，无编译步骤 |
| Windows 10/11 | ✅ 支持 | 提供 `scripts/build.ps1` |
| Python 3.8 – 3.12 | ✅ 支持 | 3.11 已完整实测 |
| 完全离线的内网环境 | ✅ 支持 | 0 依赖 + `selftest` 离线自测 |

### ⚠️ 注意事项

- 使用 `wss://` 时依赖系统根证书；自签名证书场景请加 `--insecure`（**不建议在生产使用**）。
- `bench` 是串行往返测量，结论用于**同环境横向对比**，不代表服务端并发上限。
- `--max-payload` 用于防御超大帧，默认 32 MiB；若业务消息更大，请按需调高。
- 单文件 `wslens.pyz` 需要目标机器有 Python 解释器，它不是脱离 Python 的二进制。

### ❓ 常见问题

**Q：为什么不用 `websockets` / `websocket-client`？**
A：为了做到真正的零依赖。自带实现后可以拷进任何内网机器直接运行，且协议行为完全可审计。

**Q：`check` 报"明文 ws://"告警，但我的服务在内网？**
A：内网场景这是正常的，忽略即可；若用于 CI 门禁，请用 `--require-tls` 仅对公网端点开启。

**Q：PING 全部超时？**
A：部分服务端不实现 PING/PONG（或置于代理之后）。可先用 `send` 确认连通性，`ping` 结果仅作参考。

**Q：Windows 终端乱码？**
A：请把终端代码页设为 UTF-8：`chcp 65001`，或使用 `--no-color` 输出纯文本。

---

## 🤝 贡献指南

欢迎任何形式的贡献：🐛 Bug 报告、💡 功能建议、📝 文档改进、🔧 代码 PR。

### 🔧 开发流程

```bash
git clone https://github.com/gitstq/WSLens.git
cd WSLens

python -m wslens selftest    # ① 确认基线可用
python tests/run.py          # ② 跑单元测试（44 项）
bash scripts/build.sh        # ③ 构建 + 冒烟验证
```

### 📜 提交规范（Angular 风格）

```
feat: 新增 xxx 功能
fix: 修复 xxx 问题
docs: 更新 xxx 文档
refactor: 重构 xxx 模块
test: 补充 xxx 用例
chore: 调整构建脚本
perf: 优化 xxx 性能
```

### ✅ PR 检查清单

- [ ] 代码通过 `python tests/run.py`（44 项全绿）
- [ ] 通过 `python -m wslens selftest`（7/7）
- [ ] **未引入任何第三方运行时依赖**
- [ ] 新增能力已补充对应单元测试
- [ ] 如涉及 CLI 变更，已同步更新三个语言版本的 README
- [ ] 提交信息符合 Angular 规范

### 🐛 Issue 反馈

提交时请尽量附上：

1. 完整命令行与输出（可用 `--json` 便于复现）
2. 操作系统与 Python 版本（`python --version`）
3. 目标端点是否公网可访问（不便公开可用占位符）

---

## 📄 开源协议说明

本项目基于 **MIT License** 开源，详见 [LICENSE](./LICENSE)。

- ✅ 允许商用、修改、分发、私有使用
- ✅ 允许用于闭源项目
- ⚠️ 需保留原始版权声明与许可声明
- ❌ 作者不承担任何明示或暗示的担保责任

> WSLens 仅用于**你自己拥有或已获授权**的 WebSocket 端点诊断。请遵守目标服务的使用条款与相关法律法规，勿用于未授权的探测或压测。

---

<div align="center">

**🔭 如果 WSLens 帮到了你，欢迎点个 Star ⭐**

[简体中文](./README.zh-CN.md) · [繁體中文](./README.zh-TW.md) · [English](./README.en.md)

</div>
