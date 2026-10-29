"""终端报告渲染：人类可读文本 + 结构化 JSON。"""

from __future__ import annotations

import json
from typing import Any

from .client import WSClient
from .measure import BenchStats, Check, PingStats
from .frame import Message

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
COLORS = {"ok": "\033[32m", "warn": "\033[33m", "fail": "\033[31m", "skip": "\033[90m"}


def _c(text: str, color: str) -> str:
    return f"{COLORS.get(color, '')}{text}{RESET}" if color in COLORS else text


def rule(title: str) -> str:
    """生成带表情的小标题分隔线。"""
    return f"\n{BOLD}{title}{RESET}\n{'─' * 56}"


def kv(key: str, value: Any, pad: int = 18) -> str:
    return f"  {key.ljust(pad)}{value}"


# ------------------------------------------------------------------ 体检 --


def render_check(client: WSClient, checks: list[Check]) -> str:
    hs_res = client.handshake
    lines = [rule(f"🎯 目标  {client.url}")]
    if hs_res:
        lines.append(kv("握手状态", f"HTTP {hs_res.status_code} {hs_res.reason}".strip()))
        lines.append(kv("握手耗时", f"{hs_res.elapsed_ms:.1f} ms"))
        server = hs_res.header("Server")
        if server:
            lines.append(kv("服务端标识", server))
        if hs_res.negotiated_protocol:
            lines.append(kv("子协议", hs_res.negotiated_protocol))
    if client.target.secure:
        lines.append(kv("TLS 版本", client.tls.version or "未知"))
        if client.tls.cipher:
            lines.append(kv("加密套件", client.tls.cipher))
        cert = client.tls.cert
        if cert.get("subject_cn"):
            lines.append(kv("证书 CN", cert["subject_cn"]))
        if cert.get("issuer_o"):
            lines.append(kv("签发机构", cert["issuer_o"]))
        if cert.get("expire_in_days") is not None:
            lines.append(kv("剩余有效期", f"{cert['expire_in_days']} 天 ({cert.get('expire_at')})"))

    lines.append(rule("🩺 体检结果"))
    for c in checks:
        lines.append(f"  {c.icon} {c.name:<24}{DIM}{c.detail}{RESET}")
    return "\n".join(lines)


def check_payload(client: WSClient, checks: list[Check]) -> dict:
    hs_res = client.handshake
    return {
        "url": client.url,
        "scheme": client.target.scheme,
        "host": client.target.host,
        "port": client.target.port,
        "handshake": {
            "status": hs_res.status_code if hs_res else None,
            "reason": hs_res.reason if hs_res else None,
            "elapsed_ms": round(hs_res.elapsed_ms, 3) if hs_res else None,
            "accept_ok": hs_res.accept_ok if hs_res else None,
            "negotiated_protocol": hs_res.negotiated_protocol if hs_res else None,
            "headers": hs_res.headers if hs_res else {},
        },
        "tls": {
            "version": client.tls.version,
            "cipher": client.tls.cipher,
            "verified": client.tls.verified,
            "cert": client.tls.cert,
        },
        "checks": [{"name": c.name, "status": c.status, "detail": c.detail} for c in checks],
    }


# ------------------------------------------------------------------ 心跳 --


def render_ping(url: str, stats: PingStats) -> str:
    lines = [rule(f"🏓 PING  {url}")]
    lines.append(kv("发送 / 接收", f"{stats.sent} / {stats.received}  (丢包 {stats.loss_pct}%)"))
    lines.append(kv("最小 / 平均", f"{stats.min_ms:.2f} ms / {stats.avg_ms:.2f} ms"))
    lines.append(kv("P95 / 最大", f"{stats.p95_ms:.2f} ms / {stats.max_ms:.2f} ms"))
    lines.append(kv("抖动 / 标准差", f"{stats.jitter_ms:.2f} ms / {stats.stdev_ms:.2f} ms"))
    if stats.rtts:
        spark = sparkline(stats.rtts)
        lines.append(kv("RTT 走势", spark))
    return "\n".join(lines)


def sparkline(values: list[float], width: int = 40) -> str:
    """用 Unicode 块字符画出 RTT 走势（不依赖任何第三方库）。"""
    blocks = "▁▂▃▄▅▆▇█"
    if not values:
        return ""
    lo, hi = min(values), max(values)
    span = hi - lo or 1.0
    sampled = values if len(values) <= width else _downsample(values, width)
    chars = []
    for v in sampled:
        idx = int((v - lo) / span * (len(blocks) - 1))
        chars.append(blocks[max(0, min(len(blocks) - 1, idx))])
    return "".join(chars) + f" {DIM}({lo:.1f}–{hi:.1f} ms){RESET}"


def _downsample(values: list[float], width: int) -> list[float]:
    step = len(values) / width
    out = []
    for i in range(width):
        start, end = int(i * step), max(int((i + 1) * step), int(i * step) + 1)
        chunk = values[start:end] or values[-1:]
        out.append(sum(chunk) / len(chunk))
    return out


def ping_payload(url: str, stats: PingStats) -> dict:
    return {"url": url, "ping": stats.to_dict()}


# ------------------------------------------------------------------ 吞吐 --


def render_bench(url: str, stats: BenchStats) -> str:
    lines = [rule(f"🚀 吞吐压测  {url}")]
    lines.append(kv("消息条数", f"{stats.messages} 条 × {stats.payload_bytes} 字节"))
    lines.append(kv("总耗时", f"{stats.elapsed_s:.3f} s"))
    lines.append(kv("吞吐", f"{stats.msg_per_sec} msg/s · {stats.mib_per_sec} MiB/s"))
    lines.append(kv("平均往返", f"{stats.avg_roundtrip_ms:.2f} ms"))
    lines.append(kv("P95 往返", f"{stats.p95_roundtrip_ms:.2f} ms"))
    lines.append(kv("失败条数", stats.errors))
    return "\n".join(lines)


def bench_payload(url: str, stats: BenchStats) -> dict:
    return {"url": url, "bench": stats.to_dict()}


# ------------------------------------------------------------------ 消息 --


def describe_message(msg: Message, show_bytes: bool = False) -> str:
    icon = {"text": "📝", "binary": "📦", "close": "👋", "pong": "🏓", "ping": "🏓"}.get(msg.kind, "•")
    if msg.is_text:
        body = msg.text
        if len(body) > 400:
            body = body[:400] + f"… (共 {len(msg.text)} 字符)"
        return f"{icon} text  {body}"
    if msg.is_close:
        from .frame import decode_close

        code, reason = decode_close(msg.payload)
        return f"{icon} close code={code} reason={reason or '-'}"
    if msg.is_pong:
        return f"{icon} pong  {msg.size} 字节"
    if show_bytes:
        return f"{icon} binary  {msg.payload[:64].hex()}{'…' if msg.size > 64 else ''}"
    return f"{icon} binary  {msg.size} 字节"


def to_json(data: dict) -> str:
    """统一 JSON 输出（保证中文可读）。"""
    return json.dumps(data, ensure_ascii=False, indent=2)
