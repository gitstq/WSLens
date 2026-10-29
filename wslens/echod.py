"""内置零依赖 WebSocket 回显服务器 —— 用于离线自测、演示与本地联调。

它让 ``wslens selftest`` 完全不依赖外网即可验证全链路：握手 → 收发 → 心跳 → 关闭。
同时也可以当作一个真正的本地 echo 服务使用::

    python -m wslens serve --port 8765
"""

from __future__ import annotations

import socket
import socketserver
import threading
from dataclasses import dataclass

from . import handshake as hs
from .frame import (
    CLOSE_NORMAL,
    OP_BINARY,
    OP_CLOSE,
    OP_PING,
    OP_PONG,
    OP_TEXT,
    FrameReader,
    MessageAssembler,
    decode_close,
    encode_frame,
)

BUFFER_SIZE = 65536


@dataclass
class EchoConfig:
    """回显服务器行为配置。"""

    delay_ms: float = 0.0
    prefix: str = ""
    upper: bool = False
    greeting: str = ""
    tick_ms: float = 0.0
    max_payload: int = 8 * 1024 * 1024
    timeout: float = 30.0


class _EchoHandler(socketserver.BaseRequestHandler):
    config: EchoConfig = EchoConfig()

    def handle(self) -> None:  # noqa: D102 - 框架约定方法
        sock = self.request
        sock.settimeout(self.config.timeout)
        self._lock = threading.Lock()
        self._stop = threading.Event()
        try:
            head = self._read_http_head(sock)
            key = self._header(head, "Sec-WebSocket-Key")
            if not key:
                self._reject(sock)
                return
            protocol = self._header(head, "Sec-WebSocket-Protocol")
            self._accept(sock, key, protocol)

            if self.config.greeting:
                self._send_locked(sock, OP_TEXT, self.config.greeting.encode("utf-8"))
            ticker = None
            if self.config.tick_ms > 0:
                ticker = threading.Thread(target=self._tick, args=(sock,), daemon=True)
                ticker.start()

            self._pump(sock)
        except (ConnectionError, OSError, socket.timeout, TimeoutError):
            return
        finally:
            self._stop.set()
            try:
                sock.close()
            except OSError:
                pass

    def _tick(self, sock) -> None:
        """按固定间隔主动推送消息，用于验证 ``wslens listen`` 与服务端推送场景。"""
        import datetime as _dt

        index = 0
        while not self._stop.is_set():
            if self._stop.wait(self.config.tick_ms / 1000.0):
                break
            index += 1
            stamp = _dt.datetime.now().isoformat(timespec="milliseconds")
            try:
                self._send_locked(sock, OP_TEXT, f"tick #{index} @ {stamp}".encode("utf-8"))
            except OSError:
                break

    # -------------------------------------------------------- 握手阶段 --

    @staticmethod
    def _read_http_head(sock) -> bytes:
        buf = bytearray()
        while b"\r\n\r\n" not in buf:
            chunk = sock.recv(BUFFER_SIZE)
            if not chunk:
                break
            buf += chunk
            if len(buf) > 256 * 1024:
                break
        return bytes(buf)

    @staticmethod
    def _header(raw: bytes, name: str) -> str | None:
        text = raw.decode("utf-8", errors="replace")
        lowered = name.lower()
        for line in text.split("\r\n")[1:]:
            if ":" not in line:
                continue
            k, _, v = line.partition(":")
            if k.strip().lower() == lowered:
                return v.strip()
        return None

    @staticmethod
    def _reject(sock) -> None:
        body = (
            "<!doctype html><meta charset=utf-8>"
            "<title>WSLens Echo</title>"
            "<h1>426 Upgrade Required</h1>"
            "<p>这是一个 WebSocket 端点，请使用 ws:// 或 wss:// 连接。</p>"
        ).encode("utf-8")
        resp = (
            "HTTP/1.1 426 Upgrade Required\r\n"
            "Content-Type: text/html; charset=utf-8\r\n"
            f"Content-Length: {len(body)}\r\n"
            "Connection: close\r\n\r\n"
        ).encode("utf-8")
        sock.sendall(resp + body)

    @staticmethod
    def _accept(sock, key: str, protocol: str | None) -> None:
        lines = [
            "HTTP/1.1 101 Switching Protocols",
            "Upgrade: websocket",
            "Connection: Upgrade",
            f"Sec-WebSocket-Accept: {hs.compute_accept(key)}",
            "Sec-WebSocket-Version: 13",
        ]
        if protocol:
            # 简化实现：直接回显客户端请求的第一个子协议
            lines.append(f"Sec-WebSocket-Protocol: {protocol.split(',')[0].strip()}")
        sock.sendall(("\r\n".join(lines) + "\r\n\r\n").encode("utf-8"))

    # -------------------------------------------------------- 数据阶段 --

    def _pump(self, sock) -> None:
        reader = FrameReader(sock, max_payload=self.config.max_payload, timeout=self.config.timeout)
        assembler = MessageAssembler(reader)
        while True:
            msg = assembler.read_message(timeout=self.config.timeout)
            if msg.opcode == OP_PING:
                self._send_locked(sock, OP_PONG, msg.payload)
                continue
            if msg.is_close:
                code, _reason = decode_close(msg.payload)
                self._send_locked(sock, OP_CLOSE, msg.payload or b"\x03\xe8")
                if code == CLOSE_NORMAL:
                    return
                return
            if self.config.delay_ms:
                import time

                time.sleep(self.config.delay_ms / 1000.0)
            payload = msg.payload
            if msg.is_text and self.config.upper:
                payload = msg.text.upper().encode("utf-8")
            elif msg.is_text and self.config.prefix:
                payload = (self.config.prefix + msg.text).encode("utf-8")
            self._send_locked(sock, OP_TEXT if msg.is_text else OP_BINARY, payload)

    @staticmethod
    def _send(sock, opcode: int, payload: bytes) -> None:
        # 服务端发送的帧不得掩码（RFC 6455 5.3）
        sock.sendall(encode_frame(payload, opcode=opcode, fin=True, mask=False))

    def _send_locked(self, sock, opcode: int, payload: bytes) -> None:
        with self._lock:
            self._send(sock, opcode, payload)


class EchoServer(socketserver.ThreadingTCPServer):
    """支持后台运行的回显服务器。"""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, host: str = "127.0.0.1", port: int = 0, config: EchoConfig | None = None):
        self.config = config or EchoConfig()
        super().__init__((host, port), _EchoHandler)
        _EchoHandler.config = self.config

    @property
    def url(self) -> str:
        host, port = self.server_address[:2]
        return f"ws://{host}:{port}/"


def start_background_server(
    host: str = "127.0.0.1", port: int = 0, config: EchoConfig | None = None
) -> EchoServer:
    """在后台线程启动回显服务器，并返回服务器对象（``server.url`` 可直接连接）。"""
    server = EchoServer(host=host, port=port, config=config)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05})
    thread.daemon = True
    thread.start()
    return server


def run_forever(host: str = "127.0.0.1", port: int = 8765, config: EchoConfig | None = None) -> None:
    """前台阻塞运行（供 ``wslens serve`` 使用）。"""
    server = EchoServer(host=host, port=port, config=config)
    try:
        print(f"🛰️  WSLens 回显服务器已启动: {server.url}  (Ctrl+C 退出)")
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 正在关闭…")
    finally:
        server.server_close()
