"""RFC 6455 WebSocket 帧编解码（零依赖，仅使用标准库）。

本模块实现 WebSocket 协议的数据帧层：
- 🚀 帧编码（客户端强制掩码，符合 RFC 6455 第 5.3 节要求）
- 🔍 帧解码（支持 7 / 16 / 64 位长度扩展、分片续帧、掩码还原）
- 🧩 控制帧（PING / PONG / CLOSE）与数据帧（TEXT / BINARY / CONT）
"""

from __future__ import annotations

import os
import struct
from dataclasses import dataclass

# ---------------------------------------------------------------- 操作码 --

OP_CONT = 0x0  # 续帧
OP_TEXT = 0x1  # 文本帧
OP_BINARY = 0x2  # 二进制帧
OP_CLOSE = 0x8  # 关闭帧
OP_PING = 0x9  # 心跳请求
OP_PONG = 0xA  # 心跳应答

OPCODE_NAMES = {
    OP_CONT: "continuation",
    OP_TEXT: "text",
    OP_BINARY: "binary",
    OP_CLOSE: "close",
    OP_PING: "ping",
    OP_PONG: "pong",
}

# -------------------------------------------------------------- 关闭码 --

CLOSE_NORMAL = 1000
CLOSE_GOING_AWAY = 1001
CLOSE_PROTOCOL_ERROR = 1002
CLOSE_UNSUPPORTED = 1003
CLOSE_INVALID_PAYLOAD = 1007
CLOSE_MESSAGE_TOO_BIG = 1009
CLOSE_INTERNAL_ERROR = 1011

CLOSE_REASONS = {
    CLOSE_NORMAL: "normal closure",
    CLOSE_GOING_AWAY: "going away",
    CLOSE_PROTOCOL_ERROR: "protocol error",
    CLOSE_UNSUPPORTED: "unsupported data",
    CLOSE_INVALID_PAYLOAD: "invalid payload data",
    CLOSE_MESSAGE_TOO_BIG: "message too big",
    CLOSE_INTERNAL_ERROR: "internal error",
}

# 单帧负载上限（默认 32 MiB），防止恶意服务端发来超大帧导致内存打爆
DEFAULT_MAX_PAYLOAD = 32 * 1024 * 1024


# ------------------------------------------------------------------ 异常 --


class WSFramingError(Exception):
    """帧结构非法或超出限制时抛出。"""


# ------------------------------------------------------------------ 模型 --


@dataclass
class Frame:
    """一个完整的 WebSocket 帧。"""

    fin: bool
    opcode: int
    payload: bytes = b""
    masked: bool = False

    @property
    def opcode_name(self) -> str:
        return OPCODE_NAMES.get(self.opcode, f"unknown(0x{self.opcode:x})")

    @property
    def is_control(self) -> bool:
        return bool(self.opcode & 0x8)

    @property
    def text(self) -> str:
        """以 UTF-8 解码负载；非法 UTF-8 使用替换字符，避免抛异常中断诊断。"""
        return self.payload.decode("utf-8", errors="replace")


@dataclass
class Message:
    """由一个或多个帧组装出的完整消息。"""

    opcode: int
    payload: bytes = b""
    frames: int = 1

    @property
    def is_text(self) -> bool:
        return self.opcode == OP_TEXT

    @property
    def is_binary(self) -> bool:
        return self.opcode == OP_BINARY

    @property
    def is_close(self) -> bool:
        return self.opcode == OP_CLOSE

    @property
    def is_pong(self) -> bool:
        return self.opcode == OP_PONG

    @property
    def text(self) -> str:
        return self.payload.decode("utf-8", errors="replace")

    @property
    def size(self) -> int:
        return len(self.payload)

    @property
    def kind(self) -> str:
        return OPCODE_NAMES.get(self.opcode, str(self.opcode))


# ------------------------------------------------------------------ 掩码 --


def _apply_mask(payload: bytes, key: bytes) -> bytes:
    """对负载做异或掩码（加密与解密是同一个操作）。"""
    n = len(payload)
    if n == 0 or not key:
        return payload
    stream = (key * (n // len(key) + 1))[:n]
    return (int.from_bytes(payload, "big") ^ int.from_bytes(stream, "big")).to_bytes(n, "big")


# ------------------------------------------------------------------ 编码 --


def encode_frame(
    payload: bytes,
    opcode: int = OP_TEXT,
    fin: bool = True,
    mask: bool = True,
    mask_key: bytes | None = None,
) -> bytes:
    """编码一个 WebSocket 帧。

    :param payload: 负载字节；也可传入 ``str``，会自动按 UTF-8 编码。
    :param opcode: 操作码，见模块常量。
    :param fin: 是否为消息的最后一个帧。
    :param mask: 是否掩码。RFC 6455 要求客户端发往服务端的帧必须掩码。
    :param mask_key: 指定 4 字节掩码（测试用）；默认随机生成。
    """
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    payload = bytes(payload)

    if not 0 <= opcode <= 0xF:
        raise ValueError(f"非法操作码: {opcode}")
    if opcode not in OPCODE_NAMES:
        raise ValueError(f"不支持的操作码: {opcode}")
    if opcode & 0x8 and len(payload) > 125:
        raise ValueError("控制帧负载不得超过 125 字节")
    if opcode & 0x8 and not fin:
        raise ValueError("控制帧不允许分片（FIN 必须为 1）")

    n = len(payload)
    header = bytearray()
    header.append((0x80 if fin else 0x00) | opcode)

    mask_flag = 0x80 if mask else 0x00
    if n < 126:
        header.append(mask_flag | n)
    elif n < 65536:
        header.append(mask_flag | 126)
        header += struct.pack("!H", n)
    else:
        header.append(mask_flag | 127)
        header += struct.pack("!Q", n)

    body = payload
    if mask:
        key = mask_key if mask_key is not None else os.urandom(4)
        if len(key) != 4:
            raise ValueError("掩码密钥必须是 4 字节")
        header += key
        body = _apply_mask(payload, key)

    return bytes(header) + body


def encode_close(code: int = CLOSE_NORMAL, reason: str = "") -> bytes:
    """编码一个关闭帧（负载前 2 字节为大端关闭码，其余为 UTF-8 原因）。"""
    payload = struct.pack("!H", code) + reason.encode("utf-8")
    return encode_frame(payload, opcode=OP_CLOSE, fin=True, mask=True)


def decode_close(payload: bytes) -> tuple[int, str]:
    """解析关闭帧负载，返回 ``(关闭码, 原因文本)``。"""
    if len(payload) >= 2:
        code = struct.unpack("!H", payload[:2])[0]
        reason = payload[2:].decode("utf-8", errors="replace")
        return code, reason
    return CLOSE_NORMAL, ""


# ------------------------------------------------------------------ 解码 --


class FrameReader:
    """从一个已连接的 socket 上流式读取 WebSocket 帧。

    设计要点：
    - 使用 ``recv_exact`` 保证半包/粘包都能正确切分；
    - 自动还原服务端掩码（虽然 RFC 禁止服务端掩码，但容错处理更利于诊断）；
    - 支持 ``max_payload`` 上限保护。
    """

    def __init__(self, sock, max_payload: int = DEFAULT_MAX_PAYLOAD, timeout: float | None = None):
        self._sock = sock
        self._max_payload = max_payload
        self._timeout = timeout

    def _recv_exact(self, n: int) -> bytes:
        buf = bytearray()
        while len(buf) < n:
            self._sock.settimeout(self._timeout)
            chunk = self._sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("连接在对端读取完预期字节前被关闭")
            buf += chunk
        return bytes(buf)

    def read_frame(self, timeout: float | None = None) -> Frame:
        """读取并解析单个帧。"""
        prev = self._timeout
        if timeout is not None:
            self._timeout = timeout
        try:
            head = self._recv_exact(2)
            b0, b1 = head[0], head[1]
            fin = bool(b0 & 0x80)
            rsv = b0 & 0x70
            opcode = b0 & 0x0F
            masked = bool(b1 & 0x80)
            length = b1 & 0x7F

            if rsv:
                raise WSFramingError(f"RSV 保留位被置位 (0x{rsv:02x})，违反 RFC 6455")
            if opcode not in OPCODE_NAMES:
                raise WSFramingError(f"未知操作码 0x{opcode:x}")
            if opcode & 0x8 and length > 125:
                raise WSFramingError("控制帧负载长度超过 125 字节")
            if opcode & 0x8 and not fin:
                raise WSFramingError("控制帧不允许分片")

            if length == 126:
                length = struct.unpack("!H", self._recv_exact(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", self._recv_exact(8))[0]
                if length >> 63:
                    raise WSFramingError("负载长度最高位被置位，非法")

            if length > self._max_payload:
                raise WSFramingError(
                    f"负载 {length} 字节超过上限 {self._max_payload} 字节（可用 --max-payload 调整）"
                )

            key = self._recv_exact(4) if masked else b""
            payload = self._recv_exact(length) if length else b""
            if masked:
                payload = _apply_mask(payload, key)

            return Frame(fin=fin, opcode=opcode, payload=payload, masked=masked)
        finally:
            self._timeout = prev


class MessageAssembler:
    """把连续的帧组装成完整消息（处理分片续帧与控制帧穿插）。"""

    def __init__(self, reader: FrameReader):
        self._reader = reader
        self._opcode: int | None = None
        self._buf = bytearray()
        self._frames = 0

    def read_message(self, timeout: float | None = None) -> Message:
        """读取一条完整消息。

        控制帧（PING/PONG/CLOSE）不会被合并，直接以单帧消息返回；
        数据帧会等待直到收到 FIN=1 的帧为止。
        """
        while True:
            frame = self._reader.read_frame(timeout=timeout)

            if frame.is_control:
                # 控制帧可以穿插在分片消息中间，独立返回
                return Message(opcode=frame.opcode, payload=frame.payload, frames=1)

            if frame.opcode == OP_CONT:
                if self._opcode is None:
                    raise WSFramingError("收到续帧但没有起始数据帧")
                self._buf += frame.payload
                self._frames += 1
            else:
                if self._opcode is not None:
                    raise WSFramingError("新的数据帧出现，但上一条消息尚未收到 FIN")
                self._opcode = frame.opcode
                self._buf = bytearray(frame.payload)
                self._frames = 1

            if frame.fin:
                opcode = self._opcode if self._opcode is not None else frame.opcode
                msg = Message(opcode=opcode, payload=bytes(self._buf), frames=self._frames)
                self._opcode = None
                self._buf = bytearray()
                self._frames = 0
                return msg
