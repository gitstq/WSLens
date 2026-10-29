"""WebSocket 握手（RFC 6455 第 4 节）——零依赖实现。

- 🔑 生成 ``Sec-WebSocket-Key`` 并本地校验 ``Sec-WebSocket-Accept``
- 📨 构造 HTTP/1.1 Upgrade 请求
- 📬 解析状态行与响应头（大小写不敏感）
- 🔐 读取 TLS 版本与证书信息（仅 ``wss://``）
"""

from __future__ import annotations

import base64
import hashlib
import os
from dataclasses import dataclass, field
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit

WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
DEFAULT_UA = "WSLens/1.0.0 (+https://github.com/gitstq/WSLens)"

DEFAULT_PORTS = {"ws": 80, "wss": 443, "http": 80, "https": 443}


class HandshakeError(Exception):
    """握手失败（非 101、Accept 校验失败、响应不可解析等）。"""


@dataclass
class Target:
    """解析后的连接目标。"""

    url: str
    scheme: str
    host: str
    port: int
    path: str
    secure: bool

    @property
    def netloc(self) -> str:
        return f"{self.host}:{self.port}"

    @property
    def origin(self) -> str:
        scheme = "https" if self.secure else "http"
        default = DEFAULT_PORTS[scheme]
        if self.port == default:
            return f"{scheme}://{self.host}"
        return f"{scheme}://{self.host}:{self.port}"


def parse_url(url: str) -> Target:
    """解析 WebSocket URL，补齐默认端口与路径，并做基本合法性校验。"""
    if not url:
        raise ValueError("URL 不能为空")
    if "://" not in url:
        # 允许省略协议，默认走明文 ws://
        url = "ws://" + url

    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    if scheme not in ("ws", "wss"):
        raise ValueError(f"不支持的协议 '{scheme}'，仅支持 ws:// 与 wss://")

    host = parts.hostname
    if not host:
        raise ValueError(f"无法从 URL 解析主机名: {url}")

    try:
        port = parts.port or DEFAULT_PORTS[scheme]
    except ValueError as exc:  # pragma: no cover - 端口非数字
        raise ValueError(f"URL 端口非法: {url}") from exc

    path = parts.path or "/"
    if parts.query:
        path = f"{path}?{parts.query}"

    return Target(url=url, scheme=scheme, host=host, port=port, path=path, secure=scheme == "wss")


def generate_key() -> str:
    """生成随机的 16 字节 Base64 ``Sec-WebSocket-Key``。"""
    return base64.b64encode(os.urandom(16)).decode("ascii")


def compute_accept(key: str) -> str:
    """按 RFC 6455 计算 ``Sec-WebSocket-Accept`` = Base64(SHA1(key + GUID))。"""
    digest = hashlib.sha1((key + WS_GUID).encode("utf-8")).digest()
    return base64.b64encode(digest).decode("ascii")


def build_request(
    target: Target,
    key: str,
    subprotocols: list[str] | None = None,
    extra_headers: dict[str, str] | None = None,
    origin: str | None = None,
    user_agent: str = DEFAULT_UA,
) -> bytes:
    """构造 HTTP Upgrade 请求（字节串，可直接写入 socket）。"""
    lines = [
        f"GET {target.path} HTTP/1.1",
        f"Host: {target.netloc}",
        "Upgrade: websocket",
        "Connection: Upgrade",
        f"Sec-WebSocket-Key: {key}",
        "Sec-WebSocket-Version: 13",
        f"User-Agent: {user_agent}",
    ]
    if subprotocols:
        lines.append("Sec-WebSocket-Protocol: " + ", ".join(subprotocols))
    if origin:
        lines.append(f"Origin: {origin}")
    else:
        lines.append(f"Origin: {target.origin}")

    # 自定义头放在最后，允许用户覆盖上面的默认值
    for name, value in (extra_headers or {}).items():
        lines.append(f"{name}: {value}")

    return ("\r\n".join(lines) + "\r\n\r\n").encode("utf-8")


@dataclass
class HandshakeResult:
    """握手结果快照。"""

    status_code: int
    reason: str
    headers: dict[str, str] = field(default_factory=dict)
    key: str = ""
    accept_ok: bool = False
    negotiated_protocol: str | None = None
    elapsed_ms: float = 0.0
    tls_version: str | None = None
    tls_cipher: str | None = None
    raw_response: str = ""

    def header(self, name: str) -> str | None:
        """大小写不敏感地读取响应头。"""
        lowered = name.lower()
        for k, v in self.headers.items():
            if k.lower() == lowered:
                return v
        return None


def parse_response(raw: bytes) -> tuple[int, str, dict[str, str]]:
    """解析 HTTP 响应，返回 ``(状态码, 原因短语, 头字典)``。"""
    text = raw.decode("utf-8", errors="replace")
    head, _, _ = text.partition("\r\n\r\n")
    lines = head.split("\r\n")
    if not lines or not lines[0]:
        raise HandshakeError("服务端返回为空")

    status_line = lines[0]
    parts = status_line.split(" ", 2)
    if len(parts) < 2 or not parts[1].isdigit():
        raise HandshakeError(f"无法解析状态行: {status_line!r}")
    status = int(parts[1])
    reason = parts[2] if len(parts) > 2 else ""

    headers: dict[str, str] = {}
    for line in lines[1:]:
        if not line or ":" not in line:
            continue
        name, _, value = line.partition(":")
        headers[name.strip()] = value.strip()
    return status, reason, headers


def extract_cert_info(peercert: dict | None) -> dict:
    """把 ``SSLSocket.getpeercert()`` 结果整理成诊断友好的结构。"""
    info: dict = {}
    if not peercert:
        return info

    subject = {}
    for rdn in peercert.get("subject", ()):  # ((('commonName', 'x'),), ...)
        for k, v in rdn:
            subject.setdefault(k, v)
    issuer = {}
    for rdn in peercert.get("issuer", ()):
        for k, v in rdn:
            issuer.setdefault(k, v)

    info["subject_cn"] = subject.get("commonName")
    info["subject_o"] = subject.get("organizationName")
    info["issuer_cn"] = issuer.get("commonName")
    info["issuer_o"] = issuer.get("organizationName")
    info["san"] = [v for kind, v in peercert.get("subjectAltName", ()) if kind == "DNS"]
    info["not_before"] = peercert.get("notBefore")
    info["not_after"] = peercert.get("notAfter")

    # 计算剩余有效天数（失败时静默跳过，不影响主流程）
    _KEYS = {"notBefore": ("valid_from_days", "valid_from"), "notAfter": ("expire_in_days", "expire_at")}
    for src, (days_key, at_key) in _KEYS.items():
        raw = peercert.get(src)
        if not raw:
            continue
        try:
            import datetime as _dt

            moment = parsedate_to_datetime(raw)
            if moment.tzinfo is None:
                moment = moment.replace(tzinfo=_dt.timezone.utc)
            now = _dt.datetime.now(_dt.timezone.utc)
            info[days_key] = int((moment - now).total_seconds() // 86400)
            info[at_key] = moment.astimezone().isoformat(timespec="seconds")
        except Exception:  # noqa: BLE001 - 证书时间格式异常不应中断诊断
            continue
    return info
