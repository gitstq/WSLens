"""握手与 URL 解析测试。"""

from __future__ import annotations

import unittest

from wslens import handshake as hs


class TestURL(unittest.TestCase):
    def test_defaults(self) -> None:
        t = hs.parse_url("ws://example.com")
        self.assertEqual((t.host, t.port, t.path, t.secure), ("example.com", 80, "/", False))

        t = hs.parse_url("wss://example.com/socket")
        self.assertEqual((t.host, t.port, t.path, t.secure), ("example.com", 443, "/socket", True))

    def test_scheme_without_prefix(self) -> None:
        self.assertEqual(hs.parse_url("127.0.0.1:8765").port, 8765)

    def test_query_preserved(self) -> None:
        t = hs.parse_url("wss://h.example/ws?token=abc")
        self.assertEqual(t.path, "/ws?token=abc")

    def test_bad_scheme(self) -> None:
        with self.assertRaises(ValueError):
            hs.parse_url("http://example.com")

    def test_origin(self) -> None:
        self.assertEqual(hs.parse_url("wss://h.example").origin, "https://h.example")
        self.assertEqual(hs.parse_url("ws://h.example:81").origin, "http://h.example:81")


class TestAccept(unittest.TestCase):
    def test_rfc6455_example_vector(self) -> None:
        """RFC 6455 第 1.3 节给出的标准测试向量。"""
        key = "dGhlIHNhbXBsZSBub25jZQ=="
        self.assertEqual(hs.compute_accept(key), "s3pPLMBiTxaQ9kYGzzhZRbK+xOo=")

    def test_key_is_random_base64_16_bytes(self) -> None:
        import base64

        a, b = hs.generate_key(), hs.generate_key()
        self.assertNotEqual(a, b)
        self.assertEqual(len(base64.b64decode(a)), 16)


class TestRequest(unittest.TestCase):
    def test_request_shape(self) -> None:
        target = hs.parse_url("wss://h.example:8443/ws?x=1")
        raw = hs.build_request(target, "KEYKEY", subprotocols=["chat", "echo"]).decode()
        self.assertTrue(raw.startswith("GET /ws?x=1 HTTP/1.1\r\n"))
        self.assertIn("Host: h.example:8443", raw)
        self.assertIn("Upgrade: websocket", raw)
        self.assertIn("Sec-WebSocket-Key: KEYKEY", raw)
        self.assertIn("Sec-WebSocket-Version: 13", raw)
        self.assertIn("Sec-WebSocket-Protocol: chat, echo", raw)
        self.assertTrue(raw.endswith("\r\n\r\n"))

    def test_extra_header_override(self) -> None:
        target = hs.parse_url("ws://h.example")
        raw = hs.build_request(target, "K", extra_headers={"X-Trace": "abc"}).decode()
        self.assertIn("X-Trace: abc", raw)


class TestResponse(unittest.TestCase):
    def test_parse_ok(self) -> None:
        raw = (
            b"HTTP/1.1 101 Switching Protocols\r\n"
            b"Upgrade: websocket\r\n"
            b"Connection: Upgrade\r\n"
            b"Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=\r\n\r\n"
        )
        status, reason, headers = hs.parse_response(raw)
        self.assertEqual(status, 101)
        self.assertEqual(reason, "Switching Protocols")
        self.assertEqual(headers["Upgrade"], "websocket")

    def test_case_insensitive_lookup(self) -> None:
        result = hs.HandshakeResult(status_code=101, reason="", headers={"upgrade": "WebSocket"})
        self.assertEqual(result.header("UPGRADE"), "WebSocket")

    def test_non_101(self) -> None:
        raw = b"HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\n\r\n"
        status, reason, _ = hs.parse_response(raw)
        self.assertEqual((status, reason), (404, "Not Found"))

    def test_empty_response(self) -> None:
        with self.assertRaises(hs.HandshakeError):
            hs.parse_response(b"")


if __name__ == "__main__":
    unittest.main()
