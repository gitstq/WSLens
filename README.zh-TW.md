<div align="center">

# 🔭 WSLens

**零依賴 · 離線優先的 WebSocket 診斷與效能探針**

[简体中文](./README.zh-CN.md) · [繁體中文](./README.zh-TW.md) · [English](./README.en.md)

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Dependencies](https://img.shields.io/badge/dependencies-0-brightgreen)](#-核心特性)
[![License](https://img.shields.io/badge/license-MIT-green)](#-開源協議說明)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)](#-打包與部署指南)

</div>

---

## 🎉 專案介紹

WebSocket 上線後「連得上但不好用」的問題，往往最難定位：握手真的是 101 嗎？憑證還剩幾天到期？PING/PONG 到底幾毫秒？有沒有丟包？——這些問題通常得裝 `wscat`、喬 Node 環境，或打開瀏覽器 DevTools 才回答得出來。

**WSLens** 把這套診斷能力收進一個 **零第三方依賴、純 Python 標準函式庫** 的命令列工具。它自帶完整的 RFC 6455 實作（訊框編解碼 + 握手 + 心跳），因此**不需要 `websockets`、`websocket-client` 或任何 pip 套件**，也不需要 Node.js。複製一個檔案就能在沒有外網的機器上跑起來。

### 🎯 解決什麼痛點

| 痛點 | 以前怎麼做 | WSLens 怎麼做 |
| --- | --- | --- |
| 🤔 連不上，不知卡在哪一步 | 抓封包 / 翻日誌 | `wslens check` 直接告訴你握手碼、Accept 校驗、TLS 版本 |
| 🐢 懷疑鏈路慢，但沒有數據 | 自己寫腳本或裝 Node 工具 | `wslens ping` 給出 min/avg/P95/max/抖動/丟包 |
| 🔐 憑證什麼時候過期 | `openssl s_client` 拼指令 | `check` 直接算出剩餘天數並告警 |
| 📉 想知道吞吐上限 | 找壓測平台 | `wslens bench` 本機一條指令出 msg/s 與 MiB/s |
| 🧪 CI 想做連通性門禁 | 沒有合適工具 | `--json` + 明確的結束碼，天生適配流水線 |
| 📦 內網機器裝不了依賴 | 放棄 / 手動編譯 | 0 依賴，`wslens.pyz` 單檔丟進去就能跑 |

### 💎 自研差異化亮點

- 🧬 **協定棧自己實作**：RFC 6455 訊框編解碼、遮罩、`Sec-WebSocket-Accept` 校驗全部自研，不依賴任何第三方協定庫，行為完全可控可稽核。
- 🛰️ **內建回音伺服器**：自帶一個零依賴 WebSocket 伺服端，`wslens selftest` 可在**完全離線**的環境完成端到端自測——這是絕大多數同類 CLI 沒有的能力。
- 📊 **面向診斷而非僅僅收發**：不只是「發個訊息」，而是給出統計口徑完整的延遲分佈（P95 / 抖動 / 丟包率）與 Unicode 走勢圖。
- 🤖 **CI 友善**：所有子命令支援 `--json`，結束碼語義明確，可直接作為發布門禁。
- 🪶 **單檔散佈**：除 wheel 外，建置腳本額外產出 `wslens.pyz`（zipapp 單檔可執行封存），`python wslens.pyz` 即用。

---

## ✨ 核心特性

### 🔍 協定與連線
- ✅ 完整 **RFC 6455** 訊框編解碼：7 / 16 / 64 位元長度擴充、分片續框、用戶端遮罩
- ✅ 握手校驗：**101 狀態碼**、`Sec-WebSocket-Accept` 本機重算比對、`Upgrade`/`Connection` 標頭檢查
- ✅ 支援 `ws://` 與 `wss://`（TLS），可讀取 **TLS 版本、加密套件、憑證 CN/簽發機構/剩餘天數**
- ✅ 自訂請求標頭（`-H`）、`Origin`、User-Agent、**子協定協商**（`--subprotocol`）
- ✅ 控制訊框自動處理：收到伺服端 PING 自動回 PONG；關閉訊框解析出 code 與 reason

### 📈 量測能力
- 🏓 `ping` —— 多次 PING/PONG，輸出 **min / avg / P95 / max / 標準差 / 抖動 / 丟包率** 與走勢圖
- 🚀 `bench` —— 吞吐壓測，輸出 **msg/s、MiB/s、平均往返、P95 往返、失敗數**
- 📤 `send` —— 傳送文字或二進位（含自檔案讀取），印出回音，支援 `--expect` 斷言
- 👂 `listen` —— 持續監聽伺服端推送，可限時、限筆數、印出十六進位
- 🩺 `check` —— 一次輸出 **6 項體檢結論**：握手碼 / Accept / Upgrade 標頭 / 子協定 / TLS 版本 / 憑證效期

### 🛠️ 工程化
- 🧪 `selftest` —— 離線端到端自測（7 項：握手、文字、二進位、64 位元長度、心跳、吞吐、關閉）
- 🛰️ `serve` —— 內建回音伺服器，支援人為延遲、前綴、大寫轉換、歡迎語、定時推送（模擬弱網與推送情境）
- 📦 一鍵建置：`wheel` + `wslens.pyz` 單檔產物，Windows / macOS / Linux 通吃
- 🧩 44 項單元測試，`python tests/run.py` 直接跑（不需要 pytest）
- 🎨 人類可讀彩色輸出 + `--json` 機讀輸出雙模，`--no-color` 可關閉顏色

---

## 🚀 快速開始

### 📋 環境需求

| 項目 | 需求 |
| --- | --- |
| Python | **3.8 以上**（實測 3.11） |
| 作業系統 | Windows / macOS / Linux 皆可 |
| 第三方依賴 | **無**（僅使用 Python 標準函式庫） |
| 網路 | 診斷公網端點時需要；`selftest` 完全離線 |

### ⚡ 三種安裝方式（任選其一）

**方式一：pip 安裝（推薦）**

```bash
pip install wslens
wslens --version
```

**方式二：免安裝，單檔執行**

```bash
# 從 Releases 取得 wslens.pyz，或本機建置：
python wslens.pyz --help
```

**方式三：從原始碼直接跑（零安裝）**

```bash
git clone https://github.com/gitstq/WSLens.git
cd WSLens
python -m wslens --help          # 不安裝任何東西，立即可用
```

### 🏁 30 秒上手

```bash
# ① 先離線自測，確認環境沒問題
python -m wslens selftest

# ② 起一個本機回音伺服器（另開一個終端機）
python -m wslens serve --port 8765 --greeting "👋 你好" --tick-ms 1000

# ③ 體檢
python -m wslens check ws://127.0.0.1:8765

# ④ 測延遲
python -m wslens ping ws://127.0.0.1:8765 -n 10

# ⑤ 發訊息
python -m wslens send ws://127.0.0.1:8765 -m "hello wslens" --wait 2

# ⑥ 壓吞吐
python -m wslens bench ws://127.0.0.1:8765 -n 500 -s 1024
```

### 🧪 對著公網真實端點試

```bash
python -m wslens check wss://ws.postman-echo.com/raw
python -m wslens ping  wss://echo.websocket.org -n 10
```

---

## 📖 詳細使用指南

### 🧭 命令總覽

| 命令 | 作用 | 常用參數 |
| --- | --- | --- |
| `check` | 🩺 握手與安全體檢 | `--require-tls` |
| `ping` | 🏓 PING/PONG 延遲統計 | `-n/--count`、`-i/--interval` |
| `send` | 📤 傳送並印出回音 | `-m/--message`、`--file`、`--binary`、`--wait`、`--expect` |
| `listen` | 👂 監聽伺服端推送 | `-d/--duration`、`-n/--max-messages`、`--show-bytes` |
| `bench` | 🚀 吞吐與延遲壓測 | `-n/--count`、`-s/--size`、`--binary` |
| `serve` | 🛰️ 啟動內建回音伺服器 | `-p/--port`、`--delay-ms`、`--prefix`、`--upper`、`--greeting`、`--tick-ms` |
| `selftest` | 🧪 離線端到端自測 | — |

### 🌐 全域參數（可放在子命令之前或之後）

| 參數 | 預設值 | 說明 |
| --- | --- | --- |
| `--json` | 關 | 以 JSON 輸出，便於管道與 CI 消費 |
| `-t, --timeout` | `10` | 逾時秒數 |
| `--insecure` | 關 | 跳過 TLS 憑證校驗（**僅除錯用**） |
| `--max-payload` | `33554432` | 單框負載上限（位元組），避免記憶體爆掉 |
| `-H, --header` | — | 附加請求標頭，格式 `Name: value`，可重複 |
| `--origin` | 自動 | 覆寫 `Origin` 請求標頭 |
| `--subprotocol` | — | 請求的子協定，可重複指定 |
| `--user-agent` | `WSLens/1.0.0` | 自訂 User-Agent |
| `--no-color` | 關 | 關閉彩色輸出 |

---

### 🩺 `check` —— 握手與安全體檢

```bash
wslens check wss://ws.postman-echo.com/raw
```

真實輸出範例：

```
🎯 目標  wss://ws.postman-echo.com/raw
────────────────────────────────────────────────────────
  握手狀態              HTTP 101 Switching Protocols
  握手耗時              973.6 ms
  伺服端識別             nginx
  TLS 版本            TLSv1.2
  加密套件              ECDHE-RSA-AES128-GCM-SHA256 (128 bits)
  憑證 CN             postman-echo.com
  簽發機構              Amazon
  剩餘效期             121 天 (2027-02-28T07:59:59+08:00)

🩺 體檢結果
────────────────────────────────────────────────────────
  ✅ 握手狀態碼                   HTTP 101 Switching Protocols
  ✅ Sec-WebSocket-Accept 校驗 與 RFC 6455 期望值一致
  ✅ Upgrade / Connection 標頭  Upgrade=websocket Connection=upgrade
  ⏭️ 子協定協商                   未請求或未協商子協定
  ✅ TLS 版本                  TLSv1.2 · ECDHE-RSA-AES128-GCM-SHA256 (128 bits)
  ✅ 憑證效期                   剩餘 121 天 · CN=postman-echo.com
  綜合結論              ✅ 通過
```

判定口徑：

- ✅ **通過** —— 全部檢查項正常
- ⚠️ **告警** —— 例如使用明文 `ws://`、憑證剩餘不足 14 天、TLS 低於 1.2
- ❌ **失敗** —— 非 101、Accept 校驗不符、憑證已過期；加 `--require-tls` 時明文連線也判失敗

> 💡 明文 `ws://` 預設只告警不失敗，方便本機除錯；生產門禁請加 `--require-tls`。

---

### 🏓 `ping` —— 延遲與抖動

```bash
wslens ping ws://127.0.0.1:8765 -n 10 -i 0.1
```

```
🏓 PING  ws://127.0.0.1:8765
────────────────────────────────────────────────────────
  發送 / 接收           10 / 10  (丟包 0.0%)
  最小 / 平均           0.07 ms / 0.31 ms
  P95 / 最大          1.84 ms / 1.84 ms
  抖動 / 標準差          0.27 ms / 0.58 ms
  RTT 走勢            ▁▁▁▁▁▁▁█ (0.1–1.8 ms)
```

指標意義：

| 指標 | 意義 | 怎麼讀 |
| --- | --- | --- |
| `min / avg / max` | 最小 / 平均 / 最大往返延遲 | avg 是主要參考值 |
| `P95` | 95 分位延遲 | **比 avg 更能反映長尾使用者的真實體驗** |
| `抖動 jitter` | 相鄰 RTT 差值的平均絕對值 | 越大代表鏈路越不穩定 |
| `丟包率` | 未收到 PONG 的比例 | 非 0 就要警覺連線品質 |

---

### 🚀 `bench` —— 吞吐壓測

```bash
wslens bench ws://127.0.0.1:8765 -n 300 -s 2048
```

```
🚀 吞吐壓測  ws://127.0.0.1:8765
────────────────────────────────────────────────────────
  訊息筆數              300 筆 × 2048 位元組
  總耗時               0.005 s
  吞吐                57552.9 msg/s · 112.408 MiB/s
  平均往返              0.02 ms
  P95 往返            0.02 ms
  失敗筆數              0
```

> ⚠️ 這是**序列往返**壓測（發一筆、等回音、再發下一筆），量的是「單連線的請求-回應能力」，**不是**並發極限吞吐。用來比較不同環境 / 不同伺服端的相對差異最合適。

---

### 📤 `send` —— 傳送並斷言

```bash
# 傳送文字
wslens send ws://127.0.0.1:8765 -m "hello" --wait 2

# 傳送二進位（自檔案）
wslens send ws://127.0.0.1:8765 --file ./payload.bin --binary --wait 3

# CI 斷言：必須至少收到 1 筆回音，否則結束碼非 0
wslens send wss://example.com/ws -m "ping" --expect 1 --wait 5
```

---

### 👂 `listen` —— 監聽伺服端推送

```bash
# 監聽 30 秒
wslens listen wss://example.com/feed -d 30

# 只取前 5 筆，二進位以十六進位印出
wslens listen wss://example.com/feed -n 5 --show-bytes
```

搭配內建伺服器體驗推送情境：

```bash
wslens serve --port 8765 --greeting "👋 已連線" --tick-ms 500
wslens listen ws://127.0.0.1:8765 -d 5
```

---

### 🛰️ `serve` —— 內建回音伺服器

不只是測試樁，它可以當作真實的本機除錯服務：

```bash
# 基本回音
wslens serve --port 8765

# 模擬弱網（每筆訊息延遲 200ms）
wslens serve --port 8765 --delay-ms 200

# 模擬伺服端定時推送
wslens serve --port 8765 --tick-ms 500 --greeting "👋 welcome"

# 回音時加前綴 / 轉大寫，便於區分訊息來源
wslens serve --port 8765 --prefix "[echo] " --upper
```

---

### 🧪 `selftest` —— 離線端到端自測

```bash
wslens selftest
```

```
🧪 WSLens 離線自測
────────────────────────────────────────────────────────
  ✅ 握手 101 + Accept 校驗          HTTP 101 · 1.3 ms
  ✅ 文字訊息往返                      hello wslens
  ✅ 二進位訊息往返                     256 位元組
  ✅ 64 位元長度擴充                    70000 位元組
  ✅ PING/PONG 心跳                avg 0.09 ms
  ✅ 吞吐壓測                        29559.14 msg/s
  ✅ 正常關閉                        code=1000

  📊 結果: 7/7 項通過
```

> 它會自動拉起內建回音伺服器，跑完整套鏈路後再關閉，**全程不訪問外網**。裝完先跑這個，能一次排除環境、權限、埠號等問題。

---

### 🔁 結束碼（CI 門禁用）

| 結束碼 | 意義 | 典型情境 |
| --- | --- | --- |
| `0` | ✅ 成功 | 全部正常 |
| `1` | ❌ 通用錯誤 | 參數錯誤、壓測中出現失敗筆數 |
| `2` | 🔌 連線失敗 | DNS 解析失敗、埠不通、TLS 握手失敗 |
| `3` | 🤝 握手/協定失敗 | 非 101 回應、Accept 校驗失敗 |
| `4` | ⏱️ 逾時 | 握手逾時、未收到期望筆數的訊息 |
| `5` | 🩺 體檢未通過 | `check` 中存在 ❌ 項 |

### 🤖 CI 整合範例

```bash
#!/usr/bin/env bash
set -euo pipefail

# 發布後門禁：WebSocket 端點必須可用且憑證未臨期
wslens check "wss://api.example.com/ws" --require-tls --json > report.json
code=$?

if [ $code -ne 0 ]; then
  echo "::error::WebSocket 端點體檢未通過（結束碼 $code）"
  cat report.json
  exit $code
fi

echo "✅ WebSocket 端點健康"
```

GitHub Actions 片段：

```yaml
- name: 🔭 WebSocket 健康門禁
  run: |
    pip install wslens
    wslens check "${{ secrets.WS_ENDPOINT }}" --require-tls
    wslens ping  "${{ secrets.WS_ENDPOINT }}" -n 5
```

---

### 🐍 作為 Python 函式庫使用

```python
from wslens.client import WSClient, ConnectOptions

with WSClient("wss://ws.postman-echo.com/raw", ConnectOptions(timeout=8)) as ws:
    print(ws.handshake.status_code)      # 101
    print(ws.handshake.elapsed_ms)       # 握手耗時
    ws.send_text("hello")
    print(ws.recv_message(timeout=5).text)
    print(ws.ping())                     # 往返延遲（毫秒）
```

---

## 💡 設計思路與迭代規劃

### 🏗️ 架構與模組劃分

```
wslens/
├── frame.py       # RFC 6455 訊框編解碼：遮罩、長度擴充、分片組裝
├── handshake.py   # URL 解析、Upgrade 請求建構、101 回應校驗、憑證資訊擷取
├── client.py      # 連線生命週期：建連、收發、心跳、關閉
├── measure.py     # 延遲/吞吐量測與體檢規則
├── echod.py       # 內建零依賴回音伺服器（離線自測與本機聯調）
├── report.py      # 終端呈現（文字 / JSON）
└── cli.py         # 命令列入口與子命令編排
```

分層原則：**協定層（frame/handshake）不感知業務，業務層（measure/report）不碰 socket**。如此每一層都能被單獨測試——44 項單元測試正是按這個邊界組織的。

### 🤔 關鍵技術選型

| 決策 | 選擇 | 原因 |
| --- | --- | --- |
| 語言 | **Python 標準函式庫** | 跨平台一致、無需編譯；`socket`/`ssl`/`struct`/`hashlib` 已足夠實作 RFC 6455 |
| 第三方依賴 | **0 個** | 內網、離線、稽核友善；`pip install` 永不失敗 |
| 並行模型 | **同步阻塞 IO** | 診斷情境是「一問一答」，同步模型程式碼量少、時序量測更精確 |
| 測試框架 | **unittest** | 標準函式庫自帶，讓「零依賴」承諾連測試環節也不破例 |
| 散佈型態 | **wheel + pyz** | wheel 走常規安裝；pyz 單檔滿足丟進內網即用的情境 |
| 遮罩實作 | **大整數 XOR** | 避免逐位元組 Python 迴圈，大負載下編碼開銷顯著降低 |

### 🛣️ 後續迭代規劃

- [ ] 🌐 HTTP/1.1 代理（CONNECT）與 `HTTPS_PROXY` 支援
- [ ] 🍪 握手階段的 Cookie / 自訂鑑權標頭模板（如 Bearer Token 快捷參數）
- [ ] 📉 `ping` 支援長時間運行並輸出分位數直方圖（P50/P90/P99）
- [ ] 🔁 自動重連與斷線次數統計（`--reconnect`）
- [ ] 🧵 `bench` 增加並發連線數維度（`-c/--connections`）
- [ ] 📤 支援匯出 HAR / CSV 報告，便於做趨勢比較
- [ ] 🧩 提供 MCP 伺服器型態，供 AI Agent 直接呼叫診斷能力
- [ ] 🧪 增加對 permessage-deflate 擴充的探測

### 🙌 社群貢獻方向

- 補充更多真實伺服端（如各類閘道、雲廠商 WS 閘道）的相容性案例
- 完善非 UTF-8、異常分片等邊界情境的模糊測試
- 翻譯更多語言版本的 README（日語 / 韓語 / 西班牙語等）

---

## 📦 打包與部署指南

本專案屬於 **CLI 工具類**，無需打包成桌面可執行程式，提供 wheel 與單檔封存兩種型態。

### 🛠️ 一鍵建置

```bash
# Linux / macOS / WSL
bash scripts/build.sh

# Windows（PowerShell）
powershell -ExecutionPolicy Bypass -File scripts\build.ps1

# 或者用 Makefile
make build
```

建置流程會自動完成：**清理 → 跑測試 → 建置 wheel/sdist → 產生 `wslens.pyz` → 冒煙驗證**。

產物位於 `dist/`：

```
dist/
├── wslens-1.0.0-py3-none-any.whl   # 標準 wheel，pip install 用
└── wslens.pyz                      # 單檔可執行封存（zipapp）
```

### 🚚 部署方式

**① 常規安裝**

```bash
pip install dist/wslens-1.0.0-py3-none-any.whl
wslens --version
```

**② 單檔丟進內網機器（無需安裝、無需連網）**

```bash
# 目標機器只要有 Python 3.8+
python wslens.pyz check ws://10.0.0.5:8765
python wslens.pyz selftest
```

**③ 原始碼部署**

```bash
git clone https://github.com/gitstq/WSLens.git
cd WSLens
python -m wslens selftest      # 無需 pip install
```

### ✅ 相容性矩陣

| 環境 | 狀態 | 說明 |
| --- | --- | --- |
| Linux (x86_64 / ARM) | ✅ 支援 | 已實測 Ubuntu 22.04 |
| macOS (Intel / Apple Silicon) | ✅ 支援 | 標準函式庫實作，無編譯步驟 |
| Windows 10/11 | ✅ 支援 | 提供 `scripts/build.ps1` |
| Python 3.8 – 3.12 | ✅ 支援 | 3.11 已完整實測 |
| 完全離線的內網環境 | ✅ 支援 | 0 依賴 + `selftest` 離線自測 |

### ⚠️ 注意事項

- 使用 `wss://` 時依賴系統根憑證；自簽憑證情境請加 `--insecure`（**不建議在生產使用**）。
- `bench` 是序列往返量測，結論用於**同環境橫向比較**，不代表伺服端並發上限。
- `--max-payload` 用於防禦超大訊框，預設 32 MiB；若業務訊息更大，請按需調高。
- 單檔 `wslens.pyz` 需要目標機器有 Python 直譯器，它不是脫離 Python 的二進位檔。

### ❓ 常見問題

**Q：為什麼不用 `websockets` / `websocket-client`？**
A：為了做到真正的零依賴。自帶實作後可以丟進任何內網機器直接執行，且協定行為完全可稽核。

**Q：`check` 報「明文 ws://」告警，但我的服務在內網？**
A：內網情境這是正常的，忽略即可；若用於 CI 門禁，請用 `--require-tls` 僅對公網端點開啟。

**Q：PING 全部逾時？**
A：部分伺服端不實作 PING/PONG（或置於代理之後）。可先用 `send` 確認連通性，`ping` 結果僅供參考。

**Q：Windows 終端機亂碼？**
A：請把終端機字碼頁設為 UTF-8：`chcp 65001`，或使用 `--no-color` 輸出純文字。

---

## 🤝 貢獻指南

歡迎任何形式的貢獻：🐛 Bug 回報、💡 功能建議、📝 文件改進、🔧 程式碼 PR。

### 🔧 開發流程

```bash
git clone https://github.com/gitstq/WSLens.git
cd WSLens

python -m wslens selftest    # ① 確認基線可用
python tests/run.py          # ② 跑單元測試（44 項）
bash scripts/build.sh        # ③ 建置 + 冒煙驗證
```

### 📜 提交規範（Angular 風格）

```
feat: 新增 xxx 功能
fix: 修復 xxx 問題
docs: 更新 xxx 文件
refactor: 重構 xxx 模組
test: 補充 xxx 案例
chore: 調整建置腳本
perf: 優化 xxx 效能
```

### ✅ PR 檢查清單

- [ ] 程式碼通過 `python tests/run.py`（44 項全綠）
- [ ] 通過 `python -m wslens selftest`（7/7）
- [ ] **未引入任何第三方執行時依賴**
- [ ] 新增能力已補充對應單元測試
- [ ] 如涉及 CLI 變更，已同步更新三個語言版本的 README
- [ ] 提交資訊符合 Angular 規範

### 🐛 Issue 回饋

提交時請盡量附上：

1. 完整命令列與輸出（可用 `--json` 便於重現）
2. 作業系統與 Python 版本（`python --version`）
3. 目標端點是否公網可存取（不便公開可用佔位符）

---

## 📄 開源協議說明

本專案基於 **MIT License** 開源，詳見 [LICENSE](./LICENSE)。

- ✅ 允許商用、修改、散佈、私有使用
- ✅ 允許用於閉源專案
- ⚠️ 需保留原始版權聲明與授權聲明
- ❌ 作者不承擔任何明示或暗示的擔保責任

> WSLens 僅用於**你自己擁有或已獲授權**的 WebSocket 端點診斷。請遵守目標服務的使用條款與相關法律法規，勿用於未授權的探測或壓測。

---

<div align="center">

**🔭 如果 WSLens 幫到了你，歡迎點個 Star ⭐**

[简体中文](./README.zh-CN.md) · [繁體中文](./README.zh-TW.md) · [English](./README.en.md)

</div>
