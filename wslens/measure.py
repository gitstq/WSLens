"""时延 / 吞吐统计与体检规则（纯标准库，确定性计算）。"""

from __future__ import annotations

import math
import statistics
import time
from dataclasses import dataclass, field

from .client import WSClient
from .frame import OP_BINARY, OP_TEXT

# 证书剩余有效期低于该天数时给出「即将过期」告警
CERT_WARN_DAYS = 14
# 低于该 TLS 版本视为不安全
MIN_TLS_VERSION = ("TLSv1.2", "TLSv1.3")


@dataclass
class PingStats:
    """PING/PONG 往返时延统计。"""

    rtts: list[float] = field(default_factory=list)
    sent: int = 0

    @property
    def received(self) -> int:
        return len(self.rtts)

    @property
    def lost(self) -> int:
        return max(0, self.sent - self.received)

    @property
    def loss_pct(self) -> float:
        return 0.0 if not self.sent else round(self.lost / self.sent * 100.0, 2)

    @property
    def min_ms(self) -> float:
        return min(self.rtts) if self.rtts else 0.0

    @property
    def max_ms(self) -> float:
        return max(self.rtts) if self.rtts else 0.0

    @property
    def avg_ms(self) -> float:
        return round(statistics.fmean(self.rtts), 3) if self.rtts else 0.0

    @property
    def stdev_ms(self) -> float:
        return round(statistics.pstdev(self.rtts), 3) if len(self.rtts) > 1 else 0.0

    @property
    def p95_ms(self) -> float:
        if not self.rtts:
            return 0.0
        ordered = sorted(self.rtts)
        idx = math.ceil(0.95 * len(ordered)) - 1
        return round(ordered[max(0, idx)], 3)

    @property
    def jitter_ms(self) -> float:
        """相邻 RTT 差值的平均绝对值（RFC 3550 抖动思路的简化版）。"""
        if len(self.rtts) < 2:
            return 0.0
        diffs = [abs(self.rtts[i] - self.rtts[i - 1]) for i in range(1, len(self.rtts))]
        return round(statistics.fmean(diffs), 3)

    def to_dict(self) -> dict:
        return {
            "sent": self.sent,
            "received": self.received,
            "lost": self.lost,
            "loss_pct": self.loss_pct,
            "min_ms": self.min_ms,
            "avg_ms": self.avg_ms,
            "p95_ms": self.p95_ms,
            "max_ms": self.max_ms,
            "stdev_ms": self.stdev_ms,
            "jitter_ms": self.jitter_ms,
            "rtts": [round(x, 3) for x in self.rtts],
        }


def measure_ping(
    client: WSClient, count: int = 5, interval: float = 0.2, timeout: float | None = None
) -> PingStats:
    """对已连接的客户端执行多次 PING，收集 RTT 样本。"""
    stats = PingStats(sent=count)
    for i in range(count):
        payload = f"wslens-{i}".encode()
        try:
            rtt = client.ping(payload=payload, timeout=timeout)
            stats.rtts.append(rtt)
        except Exception:  # noqa: BLE001 - 单次失败计入丢包，不中断整体测量
            pass
        if interval and i < count - 1:
            time.sleep(interval)
    return stats


@dataclass
class BenchStats:
    """吞吐压测结果。"""

    messages: int = 0
    payload_bytes: int = 0
    elapsed_s: float = 0.0
    errors: int = 0
    rtts: list[float] = field(default_factory=list)

    @property
    def total_bytes(self) -> int:
        return self.messages * self.payload_bytes

    @property
    def msg_per_sec(self) -> float:
        return round(self.messages / self.elapsed_s, 2) if self.elapsed_s else 0.0

    @property
    def mib_per_sec(self) -> float:
        return round(self.total_bytes / 1048576 / self.elapsed_s, 3) if self.elapsed_s else 0.0

    @property
    def avg_roundtrip_ms(self) -> float:
        return round(statistics.fmean(self.rtts), 3) if self.rtts else 0.0

    @property
    def p95_roundtrip_ms(self) -> float:
        if not self.rtts:
            return 0.0
        ordered = sorted(self.rtts)
        idx = math.ceil(0.95 * len(ordered)) - 1
        return round(ordered[max(0, idx)], 3)

    def to_dict(self) -> dict:
        return {
            "messages": self.messages,
            "payload_bytes": self.payload_bytes,
            "total_bytes": self.total_bytes,
            "elapsed_s": round(self.elapsed_s, 4),
            "msg_per_sec": self.msg_per_sec,
            "mib_per_sec": self.mib_per_sec,
            "avg_roundtrip_ms": self.avg_roundtrip_ms,
            "p95_roundtrip_ms": self.p95_roundtrip_ms,
            "errors": self.errors,
        }


def measure_throughput(
    client: WSClient,
    count: int = 100,
    payload_bytes: int = 1024,
    timeout: float | None = None,
    binary: bool = False,
) -> BenchStats:
    """发送 N 条消息并逐条等待回显，统计吞吐与往返时延。"""
    opcode = OP_BINARY if binary else OP_TEXT
    body = b"x" * payload_bytes if binary else ("x" * payload_bytes)
    stats = BenchStats(payload_bytes=payload_bytes)

    started = time.perf_counter()
    for _ in range(count):
        began = time.perf_counter()
        try:
            client.send(body, opcode=opcode)
            client.recv_message(timeout=timeout)
            stats.messages += 1
            stats.rtts.append((time.perf_counter() - began) * 1000.0)
        except Exception:  # noqa: BLE001 - 单条失败计入 errors
            stats.errors += 1
    stats.elapsed_s = time.perf_counter() - started
    return stats


# ------------------------------------------------------------- 体检规则 --


@dataclass
class Check:
    """一条体检项。"""

    name: str
    status: str  # ok / warn / fail / skip
    detail: str = ""

    @property
    def icon(self) -> str:
        return {"ok": "✅", "warn": "⚠️", "fail": "❌", "skip": "⏭️"}.get(self.status, "•")


def health_checks(client: WSClient, require_tls: bool = False) -> list[Check]:
    """基于握手结果生成一串体检项。"""
    hs_res = client.handshake
    checks: list[Check] = []
    if hs_res is None:
        return [Check("握手", "fail", "未完成握手")]

    checks.append(
        Check(
            "握手状态码",
            "ok" if hs_res.status_code == 101 else "fail",
            f"HTTP {hs_res.status_code} {hs_res.reason}".strip(),
        )
    )
    checks.append(
        Check(
            "Sec-WebSocket-Accept 校验",
            "ok" if hs_res.accept_ok else "fail",
            "与 RFC 6455 期望值一致" if hs_res.accept_ok else "校验不匹配",
        )
    )

    upgrade = (hs_res.header("Upgrade") or "").lower()
    connection = (hs_res.header("Connection") or "").lower()
    upgrade_ok = upgrade == "websocket" and "upgrade" in connection
    checks.append(
        Check(
            "Upgrade / Connection 头",
            "ok" if upgrade_ok else "warn",
            f"Upgrade={upgrade or '-'} Connection={connection or '-'}",
        )
    )

    if hs_res.negotiated_protocol:
        checks.append(Check("子协议协商", "ok", hs_res.negotiated_protocol))
    else:
        checks.append(Check("子协议协商", "skip", "未请求或未协商子协议"))

    if client.target.secure:
        version = client.tls.version or "未知"
        tls_ok = any(version.startswith(v) for v in MIN_TLS_VERSION)
        checks.append(
            Check(
                "TLS 版本",
                "ok" if tls_ok else "warn",
                f"{version} · {client.tls.cipher or '未知套件'}",
            )
        )
        if client.tls.verified:
            cert = client.tls.cert
            days = cert.get("expire_in_days")
            if days is None:
                checks.append(Check("证书有效期", "warn", "无法解析证书有效期"))
            elif days < 0:
                checks.append(Check("证书有效期", "fail", f"已过期 {-days} 天"))
            elif days <= CERT_WARN_DAYS:
                checks.append(Check("证书有效期", "warn", f"仅剩 {days} 天（将于 {cert.get('expire_at')} 到期）"))
            else:
                checks.append(Check("证书有效期", "ok", f"剩余 {days} 天 · CN={cert.get('subject_cn')}"))
        else:
            checks.append(Check("证书校验", "fail", "证书未被校验（可能使用了 --insecure）"))
    else:
        checks.append(
            Check("传输加密", "fail" if require_tls else "warn", "明文 ws://，生产环境建议 wss://")
        )

    return checks


def checks_to_dict(checks: list[Check]) -> list[dict]:
    return [{"name": c.name, "status": c.status, "detail": c.detail} for c in checks]


def worst_status(checks: list[Check]) -> str:
    """返回体检项中最严重的状态。"""
    for level in ("fail", "warn", "ok", "skip"):
        if any(c.status == level for c in checks):
            return level
    return "skip"
