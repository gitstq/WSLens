"""RFC 6455 帧编解码测试。"""

from __future__ import annotations

import io
import struct
import unittest

from wslens.frame import (
    CLOSE_NORMAL,
    OP_BINARY,
    OP_CLOSE,
    OP_CONT,
    OP_PING,
    OP_PONG,
    OP_TEXT,
    FrameReader,
    MessageAssembler,
    WSFramingError,
    decode_close,
    encode_close,
    encode_frame,
)


class FakeSock:
    """只实现 recv 的内存 socket，用于离线测试解码路径。"""

    def __init__(self, data: bytes):
        self._buf = io.BytesIO(data)

    def settimeout(self, _timeout) -> None:
        pass

    def recv(self, n: int) -> bytes:
        return self._buf.read(n)


class TestEncode(unittest.TestCase):
    def test_text_frame_masked(self) -> None:
        raw = encode_frame("hi", opcode=OP_TEXT, mask=True, mask_key=b"\x01\x02\x03\x04")
        self.assertEqual(raw[0], 0x81)  # FIN + TEXT
        self.assertTrue(raw[1] & 0x80)  # 掩码位置位
        self.assertEqual(raw[1] & 0x7F, 2)
        self.assertEqual(raw[2:6], b"\x01\x02\x03\x04")
        # 'h'=0x68 ^ 0x01 = 0x69='i' ; 'i'=0x69 ^ 0x02 = 0x6B='k'
        self.assertEqual(raw[6:], b"ik")

    def test_length_boundaries(self) -> None:
        for size in (0, 1, 125, 126, 65535, 65536, 70000):
            payload = b"x" * size
            raw = encode_frame(payload, opcode=OP_BINARY, mask=False)
            reader = FrameReader(FakeSock(raw), max_payload=1 << 20)
            frame = reader.read_frame(timeout=1)
            self.assertEqual(len(frame.payload), size, f"size={size} 往返失败")
            self.assertTrue(frame.fin)

    def test_length_prefix_width(self) -> None:
        self.assertEqual(encode_frame(b"x" * 125, mask=False)[1], 125)
        self.assertEqual(encode_frame(b"x" * 126, mask=False)[1], 126)
        self.assertEqual(struct.unpack("!H", encode_frame(b"x" * 126, mask=False)[2:4])[0], 126)
        self.assertEqual(encode_frame(b"x" * 65536, mask=False)[1], 127)
        self.assertEqual(
            struct.unpack("!Q", encode_frame(b"x" * 65536, mask=False)[2:10])[0], 65536
        )

    def test_control_frame_limits(self) -> None:
        with self.assertRaises(ValueError):
            encode_frame(b"x" * 126, opcode=OP_PING)
        with self.assertRaises(ValueError):
            encode_frame(b"x", opcode=OP_PING, fin=False)

    def test_unknown_opcode_rejected(self) -> None:
        with self.assertRaises(ValueError):
            encode_frame(b"x", opcode=0x5)

    def test_close_frame(self) -> None:
        raw = encode_close(CLOSE_NORMAL, "bye")
        reader = FrameReader(FakeSock(raw))
        frame = reader.read_frame(timeout=1)
        self.assertEqual(frame.opcode, OP_CLOSE)
        code, reason = decode_close(frame.payload)
        self.assertEqual((code, reason), (CLOSE_NORMAL, "bye"))


class TestDecode(unittest.TestCase):
    def test_roundtrip_masked(self) -> None:
        payload = bytes(range(256))
        raw = encode_frame(payload, opcode=OP_BINARY, mask=True)
        frame = FrameReader(FakeSock(raw)).read_frame(timeout=1)
        self.assertTrue(frame.masked)
        self.assertEqual(frame.payload, payload)

    def test_rsv_bit_rejected(self) -> None:
        raw = bytearray(encode_frame(b"x", mask=False))
        raw[0] |= 0x40  # 置位 RSV1
        with self.assertRaises(WSFramingError):
            FrameReader(FakeSock(bytes(raw))).read_frame(timeout=1)

    def test_control_frame_oversize_rejected(self) -> None:
        raw = bytearray(encode_frame(b"x", opcode=OP_PING, mask=False))
        raw[1] = 126  # 伪造超大控制帧
        raw += struct.pack("!H", 200) + b"x" * 200
        with self.assertRaises(WSFramingError):
            FrameReader(FakeSock(bytes(raw))).read_frame(timeout=1)

    def test_max_payload_guard(self) -> None:
        raw = encode_frame(b"x" * 500, mask=False)
        reader = FrameReader(FakeSock(raw), max_payload=100)
        with self.assertRaises(WSFramingError):
            reader.read_frame(timeout=1)

    def test_fragmented_message(self) -> None:
        raw = (
            encode_frame("Hel", opcode=OP_TEXT, fin=False, mask=False)
            + encode_frame("lo ", opcode=OP_CONT, fin=False, mask=False)
            + encode_frame("WS", opcode=OP_CONT, fin=True, mask=False)
        )
        msg = MessageAssembler(FrameReader(FakeSock(raw))).read_message(timeout=1)
        self.assertEqual(msg.text, "Hello WS")
        self.assertEqual(msg.frames, 3)
        self.assertTrue(msg.is_text)

    def test_orphan_continuation(self) -> None:
        raw = encode_frame("x", opcode=OP_CONT, fin=True, mask=False)
        with self.assertRaises(WSFramingError):
            MessageAssembler(FrameReader(FakeSock(raw))).read_message(timeout=1)

    def test_control_frame_interleaved(self) -> None:
        raw = (
            encode_frame("A", opcode=OP_TEXT, fin=False, mask=False)
            + encode_frame(b"ping", opcode=OP_PING, mask=False)
            + encode_frame("B", opcode=OP_CONT, fin=True, mask=False)
        )
        asm = MessageAssembler(FrameReader(FakeSock(raw)))
        first = asm.read_message(timeout=1)
        self.assertEqual(first.opcode, OP_PING)
        second = asm.read_message(timeout=1)
        self.assertEqual(second.text, "AB")


if __name__ == "__main__":
    unittest.main()
