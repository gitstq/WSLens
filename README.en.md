<div align="center">

# 🔭 WSLens

**A zero-dependency, offline-first WebSocket diagnostics & performance probe**

[简体中文](./README.zh-CN.md) · [繁體中文](./README.zh-TW.md) · [English](./README.en.md)

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Dependencies](https://img.shields.io/badge/dependencies-0-brightgreen)](#-core-features)
[![License](https://img.shields.io/badge/license-MIT-green)](#-license)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)](#-packaging--deployment)

</div>

---

## 🎉 Project Introduction

"It connects, but it feels broken" is the hardest class of WebSocket problem to pin down. Is the handshake really a 101? How many days are left on the certificate? What is the actual PING/PONG round trip? Are we dropping frames? Answering those usually means installing `wscat`, wiring up a Node toolchain, or digging through browser DevTools.

**WSLens** collapses that whole workflow into a **zero-dependency, pure-standard-library** command line tool. It ships its own complete RFC 6455 implementation — frame codec, handshake, and heartbeat — so there is **no `websockets`, no `websocket-client`, no pip package, and no Node.js**. Copy one file onto an air-gapped box and it just runs.

### 🎯 Pain points it removes

| Pain point | The old way | The WSLens way |
| --- | --- | --- |
| 🤔 Can't connect, no idea where it stalls | Packet capture / log archaeology | `wslens check` reports handshake code, Accept validation, TLS version |
| 🐢 Suspect a slow link, but have no numbers | Write a script or install a Node tool | `wslens ping` gives min/avg/P95/max/jitter/loss |
| 🔐 When does the certificate expire? | Wrestle `openssl s_client` | `check` computes remaining days and warns you |
| 📉 Need to know the throughput ceiling | Provision a load-testing platform | `wslens bench` gives msg/s and MiB/s locally |
| 🧪 Want a connectivity gate in CI | No suitable tool | `--json` plus meaningful exit codes, pipeline-ready |
| 📦 Air-gapped box, can't install deps | Give up / compile by hand | Zero deps; drop in `wslens.pyz` and run |

### 💎 What makes it different

- 🧬 **The protocol stack is ours.** RFC 6455 framing, masking and `Sec-WebSocket-Accept` validation are implemented in-repo — no third-party protocol library, and every behaviour is auditable.
- 🛰️ **A built-in echo server.** WSLens ships a zero-dependency WebSocket *server*, so `wslens selftest` performs a full end-to-end run **completely offline** — a capability most comparable CLIs simply don't have.
- 📊 **Diagnostics, not just send/receive.** It doesn't stop at "send a message"; it reports a statistically complete latency distribution (P95, jitter, loss) with a Unicode sparkline.
- 🤖 **CI-native.** Every subcommand supports `--json`, and exit codes are semantically explicit, so it drops straight into a release gate.
- 🪶 **Single-file distribution.** Besides the wheel, the build script emits `wslens.pyz` (a zipapp archive): `python wslens.pyz` and you're done.

---

## ✨ Core Features

### 🔍 Protocol & connection
- ✅ Full **RFC 6455** frame codec: 7 / 16 / 64-bit length extensions, fragmented continuation frames, client masking
- ✅ Handshake validation: **101 status**, local recomputation and comparison of `Sec-WebSocket-Accept`, `Upgrade`/`Connection` header checks
- ✅ `ws://` and `wss://` (TLS), reporting **TLS version, cipher suite, certificate CN / issuer / days remaining**
- ✅ Custom headers (`-H`), `Origin`, User-Agent, and **sub-protocol negotiation** (`--subprotocol`)
- ✅ Automatic control-frame handling: replies to server PING with PONG, and decodes close frames into code + reason

### 📈 Measurement
- 🏓 `ping` — repeated PING/PONG with **min / avg / P95 / max / stdev / jitter / loss** plus a sparkline
- 🚀 `bench` — throughput run reporting **msg/s, MiB/s, average RTT, P95 RTT, failure count**
- 📤 `send` — send text or binary (including from a file), print echoes, assert with `--expect`
- 👂 `listen` — subscribe to server pushes with duration / count limits and hex output
- 🩺 `check` — one pass, **six health verdicts**: handshake code / Accept / Upgrade headers / sub-protocol / TLS version / certificate validity

### 🛠️ Engineering
- 🧪 `selftest` — offline end-to-end self-test (7 checks: handshake, text, binary, 64-bit length, heartbeat, throughput, close)
- 🛰️ `serve` — built-in echo server with artificial delay, prefix, upper-casing, greeting and periodic push (simulates weak networks and push workloads)
- 📦 One-click build: `wheel` + `wslens.pyz`, on Windows / macOS / Linux alike
- 🧩 44 unit tests, runnable with `python tests/run.py` — pytest not required
- 🎨 Human-readable coloured output and `--json` machine output; `--no-color` disables colour

---

## 🚀 Quick Start

### 📋 Requirements

| Item | Requirement |
| --- | --- |
| Python | **3.8 or newer** (tested on 3.11) |
| OS | Any Windows / macOS / Linux |
| Third-party deps | **None** (standard library only) |
| Network | Needed for public endpoints; `selftest` is fully offline |

### ⚡ Three ways to install (pick one)

**Option 1 — pip (recommended)**

```bash
pip install wslens
wslens --version
```

**Option 2 — no install, single file**

```bash
# Grab wslens.pyz from Releases, or build it locally:
python wslens.pyz --help
```

**Option 3 — run straight from source (zero install)**

```bash
git clone https://github.com/gitstq/WSLens.git
cd WSLens
python -m wslens --help          # works immediately, nothing installed
```

### 🏁 Up and running in 30 seconds

```bash
# 1. Offline self-test first, to validate the environment
python -m wslens selftest

# 2. Start a local echo server (in another terminal)
python -m wslens serve --port 8765 --greeting "👋 hello" --tick-ms 1000

# 3. Health check
python -m wslens check ws://127.0.0.1:8765

# 4. Measure latency
python -m wslens ping ws://127.0.0.1:8765 -n 10

# 5. Send a message
python -m wslens send ws://127.0.0.1:8765 -m "hello wslens" --wait 2

# 6. Measure throughput
python -m wslens bench ws://127.0.0.1:8765 -n 500 -s 1024
```

### 🧪 Try it against a real public endpoint

```bash
python -m wslens check wss://ws.postman-echo.com/raw
python -m wslens ping  wss://echo.websocket.org -n 10
```

---

## 📖 Detailed Usage

### 🧭 Command overview

| Command | Purpose | Common flags |
| --- | --- | --- |
| `check` | 🩺 Handshake & security health check | `--require-tls` |
| `ping` | 🏓 PING/PONG latency statistics | `-n/--count`, `-i/--interval` |
| `send` | 📤 Send and print echoes | `-m/--message`, `--file`, `--binary`, `--wait`, `--expect` |
| `listen` | 👂 Listen for server pushes | `-d/--duration`, `-n/--max-messages`, `--show-bytes` |
| `bench` | 🚀 Throughput & latency benchmark | `-n/--count`, `-s/--size`, `--binary` |
| `serve` | 🛰️ Start the built-in echo server | `-p/--port`, `--delay-ms`, `--prefix`, `--upper`, `--greeting`, `--tick-ms` |
| `selftest` | 🧪 Offline end-to-end self-test | — |

### 🌐 Global flags (accepted before or after the subcommand)

| Flag | Default | Meaning |
| --- | --- | --- |
| `--json` | off | Emit JSON, ideal for pipes and CI |
| `-t, --timeout` | `10` | Timeout in seconds |
| `--insecure` | off | Skip TLS certificate verification (**debug only**) |
| `--max-payload` | `33554432` | Max single-frame payload in bytes, guards against memory blowups |
| `-H, --header` | — | Extra request header, `Name: value`, repeatable |
| `--origin` | auto | Override the `Origin` header |
| `--subprotocol` | — | Requested sub-protocol, repeatable |
| `--user-agent` | `WSLens/1.0.0` | Custom User-Agent |
| `--no-color` | off | Disable coloured output |

---

### 🩺 `check` — handshake & security health

```bash
wslens check wss://ws.postman-echo.com/raw
```

Real output:

```
🎯 Target  wss://ws.postman-echo.com/raw
────────────────────────────────────────────────────────
  Handshake              HTTP 101 Switching Protocols
  Handshake time         973.6 ms
  Server banner          nginx
  TLS version            TLSv1.2
  Cipher suite           ECDHE-RSA-AES128-GCM-SHA256 (128 bits)
  Certificate CN         postman-echo.com
  Issuer                 Amazon
  Validity remaining     121 days (2027-02-28T07:59:59+08:00)

🩺 Health check
────────────────────────────────────────────────────────
  ✅ Handshake status             HTTP 101 Switching Protocols
  ✅ Sec-WebSocket-Accept         matches the RFC 6455 expectation
  ✅ Upgrade / Connection         Upgrade=websocket Connection=upgrade
  ⏭️ Sub-protocol                 not requested / not negotiated
  ✅ TLS version                  TLSv1.2 · ECDHE-RSA-AES128-GCM-SHA256 (128 bits)
  ✅ Certificate validity         121 days left · CN=postman-echo.com
  Verdict                ✅ PASSED
```

Verdict rules:

- ✅ **Passed** — every check is healthy
- ⚠️ **Warning** — e.g. plaintext `ws://`, fewer than 14 days left on the certificate, TLS below 1.2
- ❌ **Failed** — non-101 response, Accept mismatch, expired certificate; with `--require-tls`, plaintext also fails

> 💡 Plaintext `ws://` only warns by default so local debugging stays convenient; add `--require-tls` for a production gate.

---

### 🏓 `ping` — latency & jitter

```bash
wslens ping ws://127.0.0.1:8765 -n 10 -i 0.1
```

```
🏓 PING  ws://127.0.0.1:8765
────────────────────────────────────────────────────────
  Sent / received        10 / 10  (loss 0.0%)
  Min / avg              0.07 ms / 0.31 ms
  P95 / max              1.84 ms / 1.84 ms
  Jitter / stdev         0.27 ms / 0.58 ms
  RTT trend              ▁▁▁▁▁▁▁█ (0.1–1.8 ms)
```

How to read the numbers:

| Metric | Meaning | Interpretation |
| --- | --- | --- |
| `min / avg / max` | Minimum / average / maximum RTT | `avg` is your headline number |
| `P95` | 95th-percentile latency | **Reflects tail-user experience better than `avg`** |
| `jitter` | Mean absolute delta between consecutive RTTs | Larger means a less stable link |
| `loss` | Share of PINGs that got no PONG | Anything non-zero deserves attention |

---

### 🚀 `bench` — throughput

```bash
wslens bench ws://127.0.0.1:8765 -n 300 -s 2048
```

```
🚀 Throughput  ws://127.0.0.1:8765
────────────────────────────────────────────────────────
  Messages               300 × 2048 bytes
  Elapsed                0.005 s
  Throughput             57552.9 msg/s · 112.408 MiB/s
  Avg round trip         0.02 ms
  P95 round trip         0.02 ms
  Failures               0
```

> ⚠️ This is a **serial request/response** measurement (send one, wait for the echo, send the next). It measures *single-connection round-trip capability*, **not** concurrent ceiling throughput. It is most useful for comparing environments or servers against each other.

---

### 📤 `send` — send & assert

```bash
# Send text
wslens send ws://127.0.0.1:8765 -m "hello" --wait 2

# Send binary from a file
wslens send ws://127.0.0.1:8765 --file ./payload.bin --binary --wait 3

# CI assertion: at least one echo must arrive, otherwise non-zero exit
wslens send wss://example.com/ws -m "ping" --expect 1 --wait 5
```

---

### 👂 `listen` — subscribe to server pushes

```bash
# Listen for 30 seconds
wslens listen wss://example.com/feed -d 30

# Take only the first 5 messages, printing binary as hex
wslens listen wss://example.com/feed -n 5 --show-bytes
```

Pair it with the built-in server to see pushes in action:

```bash
wslens serve --port 8765 --greeting "👋 connected" --tick-ms 500
wslens listen ws://127.0.0.1:8765 -d 5
```

---

### 🛰️ `serve` — the built-in echo server

More than a test stub, it is a genuinely useful local debugging service:

```bash
# Plain echo
wslens serve --port 8765

# Simulate a weak network (200 ms delay per message)
wslens serve --port 8765 --delay-ms 200

# Simulate periodic server push
wslens serve --port 8765 --tick-ms 500 --greeting "👋 welcome"

# Prefix or upper-case echoes to tell messages apart
wslens serve --port 8765 --prefix "[echo] " --upper
```

---

### 🧪 `selftest` — offline end-to-end self-test

```bash
wslens selftest
```

```
🧪 WSLens offline self-test
────────────────────────────────────────────────────────
  ✅ Handshake 101 + Accept        HTTP 101 · 1.3 ms
  ✅ Text round trip               hello wslens
  ✅ Binary round trip             256 bytes
  ✅ 64-bit length extension       70000 bytes
  ✅ PING/PONG heartbeat           avg 0.09 ms
  ✅ Throughput                    29559.14 msg/s
  ✅ Graceful close                code=1000

  📊 Result: 7/7 passed
```

> It spins up the internal echo server, exercises the whole stack, then tears it down — **without touching the internet**. Run this right after installing and you'll rule out environment, permission and port issues in one go.

---

### 🔁 Exit codes (for CI gates)

| Code | Meaning | Typical trigger |
| --- | --- | --- |
| `0` | ✅ Success | Everything healthy |
| `1` | ❌ Generic error | Bad arguments, failures during a benchmark run |
| `2` | 🔌 Connection failure | DNS failure, unreachable port, TLS handshake failure |
| `3` | 🤝 Handshake/protocol failure | Non-101 response, Accept mismatch |
| `4` | ⏱️ Timeout | Handshake timeout, fewer messages than expected |
| `5` | 🩺 Health check failed | `check` produced at least one ❌ |

### 🤖 CI integration example

```bash
#!/usr/bin/env bash
set -euo pipefail

# Post-deploy gate: the WebSocket endpoint must be usable with a valid certificate
wslens check "wss://api.example.com/ws" --require-tls --json > report.json
code=$?

if [ $code -ne 0 ]; then
  echo "::error::WebSocket endpoint health check failed (exit code $code)"
  cat report.json
  exit $code
fi

echo "✅ WebSocket endpoint healthy"
```

GitHub Actions snippet:

```yaml
- name: 🔭 WebSocket health gate
  run: |
    pip install wslens
    wslens check "${{ secrets.WS_ENDPOINT }}" --require-tls
    wslens ping  "${{ secrets.WS_ENDPOINT }}" -n 5
```

---

### 🐍 Use it as a Python library

```python
from wslens.client import WSClient, ConnectOptions

with WSClient("wss://ws.postman-echo.com/raw", ConnectOptions(timeout=8)) as ws:
    print(ws.handshake.status_code)      # 101
    print(ws.handshake.elapsed_ms)       # handshake duration
    ws.send_text("hello")
    print(ws.recv_message(timeout=5).text)
    print(ws.ping())                     # round trip in milliseconds
```

---

## 💡 Design Notes & Roadmap

### 🏗️ Architecture

```
wslens/
├── frame.py       # RFC 6455 codec: masking, length extension, fragmentation
├── handshake.py   # URL parsing, Upgrade request, 101 validation, certificate extraction
├── client.py      # Connection lifecycle: connect, send/recv, heartbeat, close
├── measure.py     # Latency/throughput statistics and health rules
├── echod.py       # Built-in zero-dependency echo server (offline self-test & local debugging)
├── report.py      # Terminal rendering (text / JSON)
└── cli.py         # CLI entry point and subcommand wiring
```

Layering rule: **the protocol layer (frame/handshake) knows nothing about the product, and the product layer (measure/report) never touches a socket.** That is why each layer is independently testable — and it's exactly how the 44 unit tests are organised.

### 🤔 Key technical decisions

| Decision | Choice | Rationale |
| --- | --- | --- |
| Language | **Python standard library** | Consistent cross-platform behaviour, no compilation; `socket`/`ssl`/`struct`/`hashlib` are enough for RFC 6455 |
| Third-party deps | **Zero** | Air-gapped and audit friendly; `pip install` can never fail on a resolver |
| Concurrency model | **Synchronous blocking IO** | Diagnostics are request/response; sync code is smaller and gives more precise timing |
| Test framework | **unittest** | Ships with Python, so the zero-dependency promise holds for tests too |
| Distribution | **wheel + pyz** | wheel for normal installs; pyz for "copy it onto the box" scenarios |
| Masking | **Big-integer XOR** | Avoids a per-byte Python loop, measurably cheaper on large payloads |

### 🛣️ Roadmap

- [ ] 🌐 HTTP/1.1 proxy (CONNECT) and `HTTPS_PROXY` support
- [ ] 🍪 Cookie / custom auth header templates at handshake time (e.g. a Bearer shortcut)
- [ ] 📉 Long-running `ping` with percentile histogram output (P50/P90/P99)
- [ ] 🔁 Automatic reconnect and disconnect counting (`--reconnect`)
- [ ] 🧵 Concurrency dimension for `bench` (`-c/--connections`)
- [ ] 📤 Export HAR / CSV reports for trend comparison
- [ ] 🧩 An MCP server flavour so AI agents can call the diagnostics directly
- [ ] 🧪 Probe support for the permessage-deflate extension

### 🙌 Where contributions are welcome

- Compatibility cases against more real servers (gateways, cloud vendors' WebSocket gateways)
- Fuzzing around non-UTF-8 payloads and unusual fragmentation
- More README translations (Japanese, Korean, Spanish, …)

---

## 📦 Packaging & Deployment

This is a **CLI tool**, so there is no desktop binary: you get a wheel and a single-file archive.

### 🛠️ One-click build

```bash
# Linux / macOS / WSL
bash scripts/build.sh

# Windows (PowerShell)
powershell -ExecutionPolicy Bypass -File scripts\build.ps1

# Or via the Makefile
make build
```

The build runs **clean → test → wheel/sdist → `wslens.pyz` → smoke test** automatically.

Artifacts land in `dist/`:

```
dist/
├── wslens-1.0.0-py3-none-any.whl   # standard wheel for pip install
└── wslens.pyz                      # single-file executable archive (zipapp)
```

### 🚚 Deployment options

**1. Regular install**

```bash
pip install dist/wslens-1.0.0-py3-none-any.whl
wslens --version
```

**2. Drop the single file onto an air-gapped box (no install, no network)**

```bash
# Any machine with Python 3.8+
python wslens.pyz check ws://10.0.0.5:8765
python wslens.pyz selftest
```

**3. Deploy from source**

```bash
git clone https://github.com/gitstq/WSLens.git
cd WSLens
python -m wslens selftest      # no pip install needed
```

### ✅ Compatibility matrix

| Environment | Status | Notes |
| --- | --- | --- |
| Linux (x86_64 / ARM) | ✅ Supported | Verified on Ubuntu 22.04 |
| macOS (Intel / Apple Silicon) | ✅ Supported | Pure stdlib, no compilation step |
| Windows 10/11 | ✅ Supported | Ships `scripts/build.ps1` |
| Python 3.8 – 3.12 | ✅ Supported | Fully tested on 3.11 |
| Fully offline networks | ✅ Supported | Zero deps + offline `selftest` |

### ⚠️ Caveats

- `wss://` relies on the system root store; for self-signed certificates use `--insecure` (**not recommended in production**).
- `bench` measures serial round trips, so use it for **like-for-like comparisons within one environment**, not as a server concurrency ceiling.
- `--max-payload` guards against oversized frames and defaults to 32 MiB — raise it if your messages are larger.
- `wslens.pyz` still needs a Python interpreter on the target; it is not a standalone binary.

### ❓ FAQ

**Q: Why not use `websockets` / `websocket-client`?**
A: To be genuinely zero-dependency. Owning the implementation means it runs on any air-gapped machine and every protocol behaviour is auditable.

**Q: `check` warns about plaintext `ws://`, but my service is internal.**
A: That's expected on an internal network — ignore it. For a CI gate, apply `--require-tls` only to public endpoints.

**Q: Every PING times out.**
A: Some servers don't implement PING/PONG, or sit behind a proxy that swallows them. Confirm reachability with `send` first and treat `ping` as advisory.

**Q: Garbled output on Windows terminals?**
A: Switch the console to UTF-8 with `chcp 65001`, or use `--no-color` for plain text.

---

## 🤝 Contributing

All contributions are welcome: 🐛 bug reports, 💡 feature ideas, 📝 documentation fixes, 🔧 pull requests.

### 🔧 Development workflow

```bash
git clone https://github.com/gitstq/WSLens.git
cd WSLens

python -m wslens selftest    # 1. confirm the baseline works
python tests/run.py          # 2. run the unit tests (44 of them)
bash scripts/build.sh        # 3. build + smoke test
```

### 📜 Commit convention (Angular style)

```
feat: add xxx
fix: fix xxx
docs: update xxx
refactor: restructure xxx
test: add xxx cases
chore: adjust build scripts
perf: optimise xxx
```

### ✅ PR checklist

- [ ] `python tests/run.py` passes (all 44 green)
- [ ] `python -m wslens selftest` passes (7/7)
- [ ] **No new third-party runtime dependency**
- [ ] New behaviour is covered by unit tests
- [ ] CLI changes are reflected in all three README translations
- [ ] Commit messages follow the Angular convention

### 🐛 Reporting issues

Please include:

1. The exact command and output (`--json` output helps a lot)
2. OS and Python version (`python --version`)
3. Whether the target endpoint is publicly reachable (use a placeholder if it isn't)

---

## 📄 License

Released under the **MIT License** — see [LICENSE](./LICENSE).

- ✅ Commercial use, modification, distribution and private use allowed
- ✅ Usable inside closed-source projects
- ⚠️ The original copyright and permission notice must be retained
- ❌ Provided without warranty of any kind

> WSLens is intended for diagnosing WebSocket endpoints **you own or are authorised to test**. Respect the target service's terms and applicable law, and never run it against endpoints without permission.

---

<div align="center">

**🔭 If WSLens helped you, consider leaving a Star ⭐**

[简体中文](./README.zh-CN.md) · [繁體中文](./README.zh-TW.md) · [English](./README.en.md)

</div>
