"""WebSocket 客户端（零依赖）：连接、收发、心跳探测、TLS 体检。"""

from __future__ import annotations

import socket
import ssl
import time
from dataclasses import dataclass, field
from typing import Iterator

from . import handshake as hs
from .frame import (
    CLOSE_NORMAL,
    DEFAULT_MAX_PAYLOAD,
    OP_BINARY,
    OP_CLOSE,
    OP_PING,
    OP_PONG,
    OP_TEXT,
    FrameReader,
    Message,
    MessageAssembler,
    encode_close,
    encode_frame,
)

BUFFER_SIZE = 65536


class WSError(Exception):
    """WSLens 基础异常。"""


class WSConnectError(WSError):
    """TCP / TLS 建连失败。"""


class WSTimeoutError(WSError):
    """等待数据超时。"""


class WSProtocolError(WSError):
    """协议行为异常。"""


@dataclass
class ConnectOptions:
    """连接参数。"""

    timeout: float = 10.0
    subprotocols: list[str] | None = None
    extra_headers: dict[str, str] | None = None
    origin: str | None = None
    insecure: bool = False
    user_agent: str = hs.DEFAULT_UA
    max_payload: int = DEFAULT_MAX_PAYLOAD


@dataclass
class TLSInfo:
    version: str | None = None
    cipher: str | None = None
    cert: dict = field(default_factory=dict)
    verified: bool = False


class WSClient:
    """一个轻量、可诊断的 WebSocket 客户端。

    用法::

        with WSClient("wss://example.com/socket") as c:
            c.connect()
            c.send_text("hello")
            print(c.recv_message().text)
            print(c.ping())
    """

    def __init__(self, url: str, options: ConnectOptions | None = None):
        self.url = url
        self.options = options or ConnectOptions()
        self.target = hs.parse_url(url)
        self.sock: socket.socket | None = None
        self.handshake: hs.HandshakeResult | None = None
        self.tls: TLSInfo = TLSInfo()
        self._reader: FrameReader | None = None
        self._assembler: MessageAssembler | None = None
        self.closed = False

    # ------------------------------------------------------------ 连接 --

    def connect(self) -> hs.HandshakeResult:
        """建立 TCP（或 TLS）连接并完成 WebSocket 握手。"""
        started = time.perf_counter()
        try:
            raw = socket.create_connection(
                (self.target.host, self.target.port), timeout=self.options.timeout
            )
        except (OSError, socket.gaierror) as exc:
            raise WSConnectError(f"无法连接到 {self.target.netloc}: {exc}") from exc

        if self.target.secure:
            ctx = ssl.create_default_context()
            if self.options.insecure:
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
            try:
                raw = ctx.wrap_socket(raw, server_hostname=self.target.host)
            except (ssl.SSLError, OSError) as exc:
                raw.close()
                raise WSConnectError(f"TLS 握手失败: {exc}") from exc
            self.tls.version = raw.version()
            cipher = raw.cipher()
            self.tls.cipher = f"{cipher[0]} ({cipher[2]} bits)" if cipher else None
            self.tls.cert = hs.extract_cert_info(raw.getpeercert())
            self.tls.verified = bool(raw.getpeercert())

        self.sock = raw
        self._reader = FrameReader(
            self.sock, max_payload=self.options.max_payload, timeout=self.options.timeout
        )
        self._assembler = MessageAssembler(self._reader)

        key = hs.generate_key()
        request = hs.build_request(
            self.target,
            key,
            subprotocols=self.options.subprotocols,
            extra_headers=self.options.extra_headers,
            origin=self.options.origin,
            user_agent=self.options.user_agent,
        )

        try:
            self.sock.settimeout(self.options.timeout)
            self.sock.sendall(request)
            raw_response = self._read_http_head()
        except (socket.timeout, TimeoutError) as exc:
            self.close_socket()
            raise WSTimeoutError(f"握手超时（{self.options.timeout}s）") from exc
        except OSError as exc:
            self.close_socket()
            raise WSConnectError(f"握手期间连接中断: {exc}") from exc

        status, reason, headers = hs.parse_response(raw_response)
        accept = headers.get("Sec-WebSocket-Accept") or self._header(headers, "Sec-WebSocket-Accept")
        protocol = self._header(headers, "Sec-WebSocket-Protocol")

        result = hs.HandshakeResult(
            status_code=status,
            reason=reason,
            headers=headers,
            key=key,
            accept_ok=(accept == hs.compute_accept(key)),
            negotiated_protocol=protocol,
            elapsed_ms=(time.perf_counter() - started) * 1000.0,
            tls_version=self.tls.version,
            tls_cipher=self.tls.cipher,
            raw_response=raw_response.decode("utf-8", errors="replace"),
        )
        self.handshake = result

        if status != 101:
            self.close_socket()
            raise WSError(f"服务端未返回 101 Switching Protocols，实际为 {status} {reason}".strip())
        if not result.accept_ok:
            self.close_socket()
            raise WSProtocolError(
                "Sec-WebSocket-Accept 校验失败，服务端可能不是合规的 WebSocket 端点"
            )
        return result

    def _read_http_head(self) -> bytes:
        """读到响应头结束（\\r\\n\\r\\n）为止。"""
        assert self.sock is not None
        buf = bytearray()
        while b"\r\n\r\n" not in buf:
            chunk = self.sock.recv(BUFFER_SIZE)
            if not chunk:
                break
            buf += chunk
            if len(buf) > 256 * 1024:
                break
        if not buf:
            raise WSConnectError("服务端在握手阶段关闭了连接且未返回任何数据")
        return bytes(buf)

    @staticmethod
    def _header(headers: dict[str, str], name: str) -> str | None:
        lowered = name.lower()
        for k, v in headers.items():
            if k.lower() == lowered:
                return v
        return None

    # ------------------------------------------------------------ 收发 --

    def send(self, data: bytes | str, opcode: int = OP_TEXT) -> int:
        """发送一条完整消息，返回写入的字节数（含帧头）。"""
        if self.sock is None:
            raise WSError("尚未建立连接")
        frame = encode_frame(data, opcode=opcode, fin=True, mask=True)
        self.sock.settimeout(self.options.timeout)
        self.sock.sendall(frame)
        return len(frame)

    def send_text(self, text: str) -> int:
        return self.send(text, opcode=OP_TEXT)

    def send_binary(self, data: bytes) -> int:
        return self.send(data, opcode=OP_BINARY)

    def recv_message(self, timeout: float | None = None) -> Message:
        """接收一条完整消息（自动合并分片、自动应答 PING）。"""
        if self._assembler is None or self.sock is None or self.closed:
            raise WSError("连接尚未建立或已关闭")
        deadline = None if timeout is None else time.perf_counter() + timeout
        while True:
            remaining = None if deadline is None else max(0.0, deadline - time.perf_counter())
            try:
                msg = self._assembler.read_message(timeout=remaining or self.options.timeout)
            except (socket.timeout, TimeoutError) as exc:
                raise WSTimeoutError(f"等待消息超时（{timeout or self.options.timeout}s）") from exc
            except OSError as exc:
                self.closed = True
                raise WSError(f"连接已中断: {exc}") from exc
            except ConnectionError as exc:
                self.closed = True
                raise WSError(str(exc)) from exc

            if msg.opcode == OP_PING:
                # 收到服务端 PING，按 RFC 要求自动回 PONG
                self.send(msg.payload, opcode=OP_PONG)
                continue
            if msg.is_close:
                self.closed = True
            return msg

    def iter_messages(self, timeout: float | None = None) -> Iterator[Message]:
        """持续迭代消息，遇到关闭帧或超时停止。"""
        while True:
            try:
                msg = self.recv_message(timeout=timeout)
            except (WSTimeoutError, WSError):
                return
            yield msg
            if msg.is_close:
                return

    def ping(self, payload: bytes = b"wslens", timeout: float | None = None) -> float:
        """发送 PING 并等待对应 PONG，返回往返时延（毫秒）。

        期间若收到其它消息帧（例如服务端推送），会自动跳过继续等待 PONG。
        """
        if self.sock is None:
            raise WSError("尚未建立连接")
        started = time.perf_counter()
        self.send(payload, opcode=OP_PING)
        deadline = None if timeout is None else time.perf_counter() + timeout
        while True:
            remaining = None if deadline is None else max(0.0, deadline - time.perf_counter())
            msg = self.recv_message(timeout=remaining)
            if msg.is_pong:
                if msg.payload == payload or not msg.payload:
                    return (time.perf_counter() - started) * 1000.0
                continue  # 不是本次 PING 的应答，继续等
            if msg.is_close:
                raise WSError("服务端在 PING 期间发送了关闭帧")

    def close(self, code: int = CLOSE_NORMAL, reason: str = "") -> None:
        """发送关闭帧并关闭 socket。"""
        if self.sock is not None and not self.closed:
            try:
                self.sock.settimeout(1.0)
                self.sock.sendall(encode_close(code, reason))
            except OSError:
                pass
        self.closed = True
        self.close_socket()

    def close_socket(self) -> None:
        if self.sock is not None:
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None

    # ---------------------------------------------------------- 上下文 --

    def __enter__(self) -> "WSClient":
        self.connect()
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()
