"""客户端端到端测试（使用内置回显服务器，完全离线）。"""

from __future__ import annotations

import unittest

from wslens.client import WSClient, ConnectOptions, WSConnectError, WSError
from wslens.echod import EchoConfig, start_background_server
from wslens.frame import OP_BINARY, OP_TEXT


class ClientCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = start_background_server("127.0.0.1", 0, EchoConfig(prefix="echo: "))
        cls.url = cls.server.url

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()


class TestHandshake(ClientCase):
    def test_upgrade_ok(self) -> None:
        client = WSClient(self.url, ConnectOptions(timeout=5))
        result = client.connect()
        self.assertEqual(result.status_code, 101)
        self.assertTrue(result.accept_ok)
        client.close()

    def test_subprotocol_negotiation(self) -> None:
        client = WSClient(self.url, ConnectOptions(timeout=5, subprotocols=["chat"]))
        result = client.connect()
        self.assertEqual(result.negotiated_protocol, "chat")
        client.close()

    def test_connection_refused(self) -> None:
        client = WSClient("ws://127.0.0.1:1", ConnectOptions(timeout=2))
        with self.assertRaises(WSConnectError):
            client.connect()

    def test_context_manager(self) -> None:
        with WSClient(self.url, ConnectOptions(timeout=5)) as client:
            self.assertEqual(client.handshake.status_code, 101)
        self.assertTrue(client.closed)


class TestMessaging(ClientCase):
    def test_text_roundtrip(self) -> None:
        with WSClient(self.url, ConnectOptions(timeout=5)) as c:
            c.send_text("hello")
            self.assertEqual(c.recv_message(timeout=5).text, "echo: hello")

    def test_binary_roundtrip(self) -> None:
        blob = bytes(range(128))
        with WSClient(self.url, ConnectOptions(timeout=5)) as c:
            c.send(blob, opcode=OP_BINARY)
            msg = c.recv_message(timeout=5)
            self.assertTrue(msg.is_binary)
            self.assertEqual(msg.payload, blob)

    def test_large_message_64bit_length(self) -> None:
        payload = "A" * 70000
        with WSClient(self.url, ConnectOptions(timeout=10)) as c:
            c.send_text(payload)
            # 回显服务器带 "echo: " 前缀，故回包比原始负载多 6 字节
            self.assertEqual(c.recv_message(timeout=10).size, 70000 + len("echo: "))

    def test_ping_pong(self) -> None:
        with WSClient(self.url, ConnectOptions(timeout=5)) as c:
            rtt = c.ping(payload=b"abc", timeout=5)
            self.assertGreaterEqual(rtt, 0.0)

    def test_utf8_multibyte(self) -> None:
        with WSClient(self.url, ConnectOptions(timeout=5)) as c:
            c.send_text("探针 🚀 测试")
            self.assertEqual(c.recv_message(timeout=5).text, "echo: 探针 🚀 测试")

    def test_close_then_recv_fails(self) -> None:
        c = WSClient(self.url, ConnectOptions(timeout=5))
        c.connect()
        c.close()
        with self.assertRaises(WSError):
            c.recv_message(timeout=2)


if __name__ == "__main__":
    unittest.main()
