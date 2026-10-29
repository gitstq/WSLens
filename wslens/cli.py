"""WSLens —— 零依赖 WebSocket 诊断与性能探针 CLI。"""

from __future__ import annotations

import argparse
import socket
import sys
import time

from . import __version__
from . import handshake as hs
from .client import (
    WSClient,
    ConnectOptions,
    WSConnectError,
    WSError,
    WSProtocolError,
    WSTimeoutError,
)
from .echod import EchoConfig, run_forever, start_background_server
from .frame import OP_BINARY, OP_TEXT
from . import measure
from . import report as R

# ------------------------------------------------------------ 退出码 --
EXIT_OK = 0
EXIT_ERROR = 1  # 通用错误
EXIT_CONNECT = 2  # TCP/TLS 建连失败
EXIT_HANDSHAKE = 3  # 握手或协议错误
EXIT_TIMEOUT = 4  # 超时
EXIT_UNHEALTHY = 5  # 体检存在 fail 项

PROG = "wslens"
EPILOG = (
    "示例:\n"
    "  wslens check wss://echo.websocket.org\n"
    "  wslens ping wss://echo.websocket.org -n 10\n"
    "  wslens send wss://echo.websocket.org -m 'hello' --wait 3\n"
    "  wslens bench wss://echo.websocket.org -n 200 -s 1024\n"
    "  wslens serve --port 8765        # 启动内置回显服务器\n"
    "  wslens selftest                 # 离线端到端自测\n"
)


def _common(suppress: bool = False) -> argparse.ArgumentParser:
    """全局公共选项。

    :param suppress: 子命令中复用时隐藏帮助，避免 ``--help`` 出现重复条目。
    """
    help_text = argparse.SUPPRESS if suppress else None
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--json", action="store_true", help=help_text or "以 JSON 输出（便于 CI/CD 消费）")
    p.add_argument("-t", "--timeout", type=float, default=10.0,
                   help=help_text or "超时秒数（默认 10）")
    p.add_argument("--insecure", action="store_true",
                   help=help_text or "跳过 TLS 证书校验（仅调试用）")
    p.add_argument("--max-payload", type=int, default=32 * 1024 * 1024,
                   help=help_text or "单帧负载上限字节数")
    p.add_argument("-H", "--header", action="append", default=[], metavar="NAME: VALUE",
                   help=help_text or "附加请求头，可重复指定")
    p.add_argument("--origin", default=None, help=help_text or "覆盖 Origin 请求头")
    p.add_argument("--subprotocol", action="append", default=[], dest="subprotocols",
                   help=help_text or "请求的子协议，可重复指定")
    p.add_argument("--user-agent", default=hs.DEFAULT_UA, help=help_text or "自定义 User-Agent")
    p.add_argument("--no-color", action="store_true", help=help_text or "关闭彩色输出")
    return p


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG,
        description="🔭 WSLens —— 零依赖、离线优先的 WebSocket 诊断与性能探针",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=EPILOG,
        parents=[_common()],
    )
    parser.add_argument("--version", action="version", version=f"{PROG} {__version__}")

    sub = parser.add_subparsers(dest="command", metavar="<命令>")
    common = _common(suppress=True)

    p_check = sub.add_parser("check", parents=[common], help="🩺 握手与安全体检")
    p_check.add_argument("url")
    p_check.add_argument("--require-tls", action="store_true", help="明文 ws:// 视为失败")

    p_ping = sub.add_parser("ping", parents=[common], help="🏓 PING/PONG 往返时延统计")
    p_ping.add_argument("url")
    p_ping.add_argument("-n", "--count", type=int, default=5, help="探测次数（默认 5）")
    p_ping.add_argument("-i", "--interval", type=float, default=0.2, help="探测间隔秒数")

    p_send = sub.add_parser("send", parents=[common], help="📤 发送消息并打印回显")
    p_send.add_argument("url")
    p_send.add_argument("-m", "--message", default=None, help="要发送的文本")
    p_send.add_argument("--file", default=None, help="从文件读取内容发送")
    p_send.add_argument("--binary", action="store_true", help="以二进制帧发送")
    p_send.add_argument("--wait", type=float, default=2.0, help="发送后等待回显的秒数")
    p_send.add_argument("--expect", type=int, default=0, help="期望收到的消息条数（用于断言）")

    p_listen = sub.add_parser("listen", parents=[common], help="👂 持续监听并输出消息")
    p_listen.add_argument("url")
    p_listen.add_argument("-d", "--duration", type=float, default=10.0, help="监听秒数")
    p_listen.add_argument("-n", "--max-messages", type=int, default=0, help="最多输出条数（0=不限）")
    p_listen.add_argument("--show-bytes", action="store_true", help="二进制消息打印十六进制")

    p_bench = sub.add_parser("bench", parents=[common], help="🚀 吞吐与往返时延压测")
    p_bench.add_argument("url")
    p_bench.add_argument("-n", "--count", type=int, default=100, help="消息条数（默认 100）")
    p_bench.add_argument("-s", "--size", type=int, default=1024, help="单条负载字节数（默认 1024）")
    p_bench.add_argument("--binary", action="store_true", help="使用二进制帧")

    p_serve = sub.add_parser("serve", parents=[common], help="🛰️  启动内置回显服务器")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("-p", "--port", type=int, default=8765)
    p_serve.add_argument("--delay-ms", type=float, default=0.0, help="每条消息人为延迟（模拟弱网）")
    p_serve.add_argument("--prefix", default="", help="回显内容前缀")
    p_serve.add_argument("--upper", action="store_true", help="回显内容转大写")
    p_serve.add_argument("--greeting", default="", help="连接建立后立即推送的欢迎消息")
    p_serve.add_argument("--tick-ms", type=float, default=0.0,
                         help="每隔 N 毫秒主动推送一条消息（模拟服务端推送）")

    sub.add_parser("selftest", parents=[common], help="🧪 离线端到端自测（内置回显服务器）")

    return parser


def parse_headers(items: list[str]) -> dict[str, str]:
    headers: dict[str, str] = {}
    for item in items:
        if ":" not in item:
            raise ValueError(f"请求头格式应为 'Name: value'，收到: {item!r}")
        name, _, value = item.partition(":")
        headers[name.strip()] = value.strip()
    return headers


def make_options(args) -> ConnectOptions:
    return ConnectOptions(
        timeout=args.timeout,
        subprotocols=args.subprotocols or None,
        extra_headers=parse_headers(args.header),
        origin=args.origin,
        insecure=args.insecure,
        user_agent=args.user_agent,
        max_payload=args.max_payload,
    )


def out(text: str) -> None:
    print(text)


def emit(args, payload: dict | None, text: str) -> None:
    """按 --json 开关选择输出形态。"""
    if args.json and payload is not None:
        print(R.to_json(payload))
    elif not args.json:
        print(text)


# -------------------------------------------------------------- 子命令 --


def cmd_check(args) -> int:
    client = WSClient(args.url, make_options(args))
    try:
        client.connect()
    except WSConnectError as exc:
        emit(args, {"url": args.url, "error": str(exc)}, f"❌ {exc}")
        return EXIT_CONNECT
    except WSTimeoutError as exc:
        emit(args, {"url": args.url, "error": str(exc)}, f"⏱️  {exc}")
        return EXIT_TIMEOUT
    except (WSError, WSProtocolError) as exc:
        emit(args, {"url": args.url, "error": str(exc)}, f"❌ {exc}")
        return EXIT_HANDSHAKE

    checks = measure.health_checks(client, require_tls=args.require_tls)
    payload = R.check_payload(client, checks)
    text = R.render_check(client, checks)
    worst = measure.worst_status(checks)
    text += "\n" + R.kv("综合结论", {"ok": "✅ 通过", "warn": "⚠️  存在告警",
                                     "fail": "❌ 存在问题", "skip": "⏭️  已跳过"}.get(worst, worst))
    emit(args, payload, text)
    client.close()
    if worst == "fail":
        return EXIT_UNHEALTHY
    return EXIT_OK


def cmd_ping(args) -> int:
    client = WSClient(args.url, make_options(args))
    try:
        client.connect()
    except WSConnectError as exc:
        emit(args, {"url": args.url, "error": str(exc)}, f"❌ {exc}")
        return EXIT_CONNECT
    except (WSError, WSTimeoutError) as exc:
        emit(args, {"url": args.url, "error": str(exc)}, f"❌ {exc}")
        return EXIT_HANDSHAKE

    stats = measure.measure_ping(
        client, count=max(1, args.count), interval=args.interval, timeout=args.timeout
    )
    emit(args, R.ping_payload(args.url, stats), R.render_ping(args.url, stats))
    client.close()
    return EXIT_OK if stats.loss_pct < 100 else EXIT_TIMEOUT


def cmd_send(args) -> int:
    if args.message is None and args.file is None:
        out("❌ 请用 -m/--message 或 --file 指定要发送的内容")
        return EXIT_ERROR
    body: bytes | str
    if args.file:
        with open(args.file, "rb") as fh:
            raw = fh.read()
        body = raw if args.binary else raw.decode("utf-8", errors="replace")
    else:
        body = args.message or ""
        if args.binary:
            body = body.encode("utf-8")

    client = WSClient(args.url, make_options(args))
    try:
        client.connect()
    except WSConnectError as exc:
        emit(args, {"url": args.url, "error": str(exc)}, f"❌ {exc}")
        return EXIT_CONNECT
    except (WSError, WSTimeoutError) as exc:
        emit(args, {"url": args.url, "error": str(exc)}, f"❌ {exc}")
        return EXIT_HANDSHAKE

    started = time.perf_counter()
    client.send(body, opcode=OP_BINARY if args.binary else OP_TEXT)
    sent_ms = (time.perf_counter() - started) * 1000.0

    messages = []
    deadline = time.perf_counter() + max(0.0, args.wait)
    while time.perf_counter() < deadline:
        remaining = deadline - time.perf_counter()
        try:
            msg = client.recv_message(timeout=remaining)
        except WSTimeoutError:
            break
        except WSError:
            break
        messages.append(msg)
        if msg.is_close:
            break
        if args.expect and len(messages) >= args.expect:
            break

    payload = {
        "url": args.url,
        "sent_bytes": len(body) if isinstance(body, (bytes, bytearray)) else len(body.encode()),
        "sent_ms": round(sent_ms, 3),
        "received": [
            {"kind": m.kind, "size": m.size, "text": m.text if m.is_text else None}
            for m in messages
        ],
    }
    if not args.json:
        out(R.rule(f"📤 发送  {args.url}"))
        out(R.kv("已发送", f"{payload['sent_bytes']} 字节 ({sent_ms:.2f} ms)"))
        out(R.rule("📥 收到回显"))
        if not messages:
            out("  （在等待窗口内没有收到任何消息）")
        for m in messages:
            out("  " + R.describe_message(m, show_bytes=True))
    else:
        print(R.to_json(payload))
    client.close()

    if args.expect and len(messages) < args.expect:
        return EXIT_TIMEOUT
    return EXIT_OK


def cmd_listen(args) -> int:
    client = WSClient(args.url, make_options(args))
    try:
        client.connect()
    except WSConnectError as exc:
        emit(args, {"url": args.url, "error": str(exc)}, f"❌ {exc}")
        return EXIT_CONNECT
    except (WSError, WSTimeoutError) as exc:
        emit(args, {"url": args.url, "error": str(exc)}, f"❌ {exc}")
        return EXIT_HANDSHAKE

    if not args.json:
        out(R.rule(f"👂 监听  {args.url}"))
        out(f"  ⏳ 最长 {args.duration}s，Ctrl+C 可随时退出\n")

    count = 0
    deadline = time.perf_counter() + args.duration
    records = []
    try:
        while time.perf_counter() < deadline:
            if args.max_messages and count >= args.max_messages:
                break
            remaining = deadline - time.perf_counter()
            try:
                msg = client.recv_message(timeout=remaining)
            except WSTimeoutError:
                break
            except WSError:
                break
            count += 1
            records.append({"kind": msg.kind, "size": msg.size,
                            "text": msg.text if msg.is_text else None})
            if not args.json:
                out("  " + R.describe_message(msg, show_bytes=args.show_bytes))
            if msg.is_close:
                break
    except KeyboardInterrupt:
        pass

    if args.json:
        print(R.to_json({"url": args.url, "duration": args.duration, "count": count,
                         "messages": records}))
    else:
        out(f"\n  📊 共收到 {count} 条消息")
    client.close()
    return EXIT_OK


def cmd_bench(args) -> int:
    client = WSClient(args.url, make_options(args))
    try:
        client.connect()
    except WSConnectError as exc:
        emit(args, {"url": args.url, "error": str(exc)}, f"❌ {exc}")
        return EXIT_CONNECT
    except (WSError, WSTimeoutError) as exc:
        emit(args, {"url": args.url, "error": str(exc)}, f"❌ {exc}")
        return EXIT_HANDSHAKE

    stats = measure.measure_throughput(
        client,
        count=max(1, args.count),
        payload_bytes=max(1, args.size),
        timeout=args.timeout,
        binary=args.binary,
    )
    emit(args, R.bench_payload(args.url, stats), R.render_bench(args.url, stats))
    client.close()
    return EXIT_OK if stats.errors == 0 else EXIT_ERROR


def cmd_serve(args) -> int:
    run_forever(
        host=args.host,
        port=args.port,
        config=EchoConfig(
            delay_ms=args.delay_ms,
            prefix=args.prefix,
            upper=args.upper,
            greeting=args.greeting,
            tick_ms=args.tick_ms,
        ),
    )
    return EXIT_OK


def cmd_selftest(args) -> int:
    """离线端到端自测：握手 → 收发 → 分片 → 心跳 → 吞吐 → 关闭。"""
    steps: list[tuple[str, bool, str]] = []

    def record(name: str, ok: bool, detail: str = "") -> None:
        steps.append((name, ok, detail))
        if not args.json:
            out(f"  {'✅' if ok else '❌'} {name:<28}{detail}")

    if not args.json:
        out(R.rule("🧪 WSLens 离线自测"))

    server = start_background_server("127.0.0.1", 0, EchoConfig())
    client = WSClient(server.url, ConnectOptions(timeout=5.0))
    exit_code = EXIT_OK
    try:
        hs_res = client.connect()
        record("握手 101 + Accept 校验", hs_res.status_code == 101 and hs_res.accept_ok,
               f"HTTP {hs_res.status_code} · {hs_res.elapsed_ms:.1f} ms")

        client.send_text("hello wslens")
        msg = client.recv_message(timeout=5.0)
        record("文本消息往返", msg.is_text and msg.text == "hello wslens", msg.text)

        blob = bytes(range(256))
        client.send_binary(blob)
        msg = client.recv_message(timeout=5.0)
        record("二进制消息往返", msg.is_binary and msg.payload == blob, f"{msg.size} 字节")

        # 大消息（>65535，验证 64 位长度扩展）
        big = "A" * 70000
        client.send_text(big)
        msg = client.recv_message(timeout=10.0)
        record("64 位长度扩展", msg.size == len(big), f"{msg.size} 字节")

        stats = measure.measure_ping(client, count=5, interval=0.05)
        record("PING/PONG 心跳", stats.received == 5, f"avg {stats.avg_ms:.2f} ms")

        bench = measure.measure_throughput(client, count=50, payload_bytes=512)
        record("吞吐压测", bench.errors == 0, f"{bench.msg_per_sec} msg/s")

        client.close()
        record("正常关闭", client.closed, "code=1000")
    except Exception as exc:  # noqa: BLE001 - 自测要如实暴露任何异常
        record("执行异常", False, f"{type(exc).__name__}: {exc}")
        exit_code = EXIT_ERROR
    finally:
        server.shutdown()
        server.server_close()

    passed = sum(1 for _, ok, _ in steps if ok)
    total = len(steps)
    if args.json:
        print(R.to_json({
            "total": total, "passed": passed,
            "steps": [{"name": n, "ok": ok, "detail": d} for n, ok, d in steps],
        }))
    else:
        out(f"\n  📊 结果: {passed}/{total} 项通过")
    return exit_code if passed != total else EXIT_OK


COMMANDS = {
    "check": cmd_check,
    "ping": cmd_ping,
    "send": cmd_send,
    "listen": cmd_listen,
    "bench": cmd_bench,
    "serve": cmd_serve,
    "selftest": cmd_selftest,
}


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.no_color:
        for key in R.COLORS:
            R.COLORS[key] = ""
        R.BOLD = R.DIM = R.RESET = ""

    if not args.command:
        parser.print_help()
        return EXIT_ERROR

    try:
        return COMMANDS[args.command](args)
    except ValueError as exc:
        out(f"❌ 参数错误: {exc}")
        return EXIT_ERROR
    except KeyboardInterrupt:
        out("\n👋 已中断")
        return EXIT_ERROR
    except socket.timeout:
        out("⏱️  操作超时")
        return EXIT_TIMEOUT


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
