# 📝 更新日志 · Changelog

本项目所有值得记录的变更都会写在这里，格式参考 [Keep a Changelog](https://keepachangelog.com/)，版本号遵循 [Semantic Versioning](https://semver.org/)。

## [1.0.0] — 2026-10-30

首个正式版本。

### ✨ 新增

- **协议层**
  - `wslens/frame.py`：完整的 RFC 6455 数据帧编解码，支持 7 / 16 / 64 位长度扩展、分片续帧组装、客户端掩码（大整数异或优化）、控制帧校验、单帧负载上限保护
  - `wslens/handshake.py`：URL 解析、`Sec-WebSocket-Key/Accept` 生成与校验、HTTP Upgrade 请求构造、响应头大小写不敏感解析、TLS 证书信息提取（CN / 签发机构 / 剩余天数）
- **客户端**
  - `wslens/client.py`：`ws://` 与 `wss://` 建连、自定义请求头 / Origin / User-Agent、子协议协商、自动应答服务端 PING、PING/PONG 往返时延测量
- **测量与体检**
  - `wslens/measure.py`：RTT 统计（min / avg / P95 / max / 标准差 / 抖动 / 丢包率）、吞吐压测（msg/s、MiB/s、平均与 P95 往返）、6 项握手与安全体检规则
- **输出**
  - `wslens/report.py`：人类可读彩色文本渲染 + `--json` 机读输出，Unicode 走势图，中文不被转义
- **内置服务**
  - `wslens/echod.py`：零依赖回显服务器，支持人为延迟、前缀、大写转换、欢迎语、定时推送
- **命令行**
  - 子命令：`check` / `ping` / `send` / `listen` / `bench` / `serve` / `selftest`
  - 全局参数：`--json`、`-t/--timeout`、`--insecure`、`--max-payload`、`-H/--header`、`--origin`、`--subprotocol`、`--user-agent`、`--no-color`
  - 明确语义的退出码：0 成功 / 1 通用错误 / 2 连接失败 / 3 握手失败 / 4 超时 / 5 体检未通过
- **工程化**
  - `pyproject.toml`（setuptools + 控制台脚本 `wslens`）、`requirements.txt`（零依赖声明）、`MANIFEST.in`、`.gitignore`、`.env.example`
  - `scripts/build.sh` 与 `scripts/build.ps1` 一键构建：wheel + `wslens.pyz` 单文件可执行归档（zipapp）
  - `Makefile` 常用任务入口
  - 44 项单元测试（标准库 `unittest`，`python tests/run.py` 直接运行）
  - 三语 README：简体中文 / 繁體中文 / English

### 🐛 修复

- 修正证书到期时间键名不一致导致的 `(None)` 显示
- 修正全局 `-s` 与 `bench --size` 的参数冲突
- 修正 zipapp 打包目录层级，使单文件 `wslens.pyz` 可正常导入子模块
- 连接关闭后再调用接收接口，改为抛出明确的 `WSError` 而非底层 `OSError`

### ✅ 验证

- 单元测试 44/44 通过
- `selftest` 离线端到端自测 7/7 通过
- 公网真实端点实测通过：`wss://ws.postman-echo.com/raw`、`wss://echo.websocket.org`
- 构建产物冒烟验证通过：`python dist/wslens.pyz selftest`
