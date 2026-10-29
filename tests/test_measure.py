"""统计与体检规则测试。"""

from __future__ import annotations

import unittest

from wslens import measure
from wslens.client import WSClient, ConnectOptions
from wslens.echod import EchoConfig, start_background_server


class TestPingStats(unittest.TestCase):
    def test_basic_stats(self) -> None:
        stats = measure.PingStats(rtts=[10.0, 20.0, 30.0, 40.0], sent=5)
        self.assertEqual(stats.received, 4)
        self.assertEqual(stats.lost, 1)
        self.assertEqual(stats.loss_pct, 20.0)
        self.assertEqual(stats.min_ms, 10.0)
        self.assertEqual(stats.max_ms, 40.0)
        self.assertEqual(stats.avg_ms, 25.0)
        self.assertEqual(stats.jitter_ms, 10.0)

    def test_empty(self) -> None:
        stats = measure.PingStats(sent=3)
        self.assertEqual((stats.avg_ms, stats.p95_ms, stats.stdev_ms), (0.0, 0.0, 0.0))
        self.assertEqual(stats.loss_pct, 100.0)

    def test_p95(self) -> None:
        stats = measure.PingStats(rtts=list(range(1, 101)), sent=100)
        self.assertGreaterEqual(stats.p95_ms, 90.0)

    def test_to_dict_keys(self) -> None:
        keys = set(measure.PingStats(rtts=[1.0], sent=1).to_dict())
        for key in ("sent", "received", "lost", "loss_pct", "min_ms", "avg_ms", "p95_ms",
                    "max_ms", "stdev_ms", "jitter_ms"):
            self.assertIn(key, keys)


class TestBenchStats(unittest.TestCase):
    def test_rates(self) -> None:
        stats = measure.BenchStats(messages=100, payload_bytes=1024, elapsed_s=2.0, rtts=[1.0, 2.0])
        self.assertEqual(stats.msg_per_sec, 50.0)
        self.assertEqual(stats.total_bytes, 102400)
        self.assertAlmostEqual(stats.mib_per_sec, 0.049, places=3)
        self.assertEqual(stats.avg_roundtrip_ms, 1.5)


class TestHealthChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = start_background_server("127.0.0.1", 0, EchoConfig())
        cls.url = cls.server.url

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()

    def test_plaintext_warns(self) -> None:
        client = WSClient(self.url, ConnectOptions(timeout=5))
        client.connect()
        checks = measure.health_checks(client)
        names = {c.name: c.status for c in checks}
        self.assertEqual(names["握手状态码"], "ok")
        self.assertEqual(names["Sec-WebSocket-Accept 校验"], "ok")
        self.assertEqual(names["传输加密"], "warn")
        client.close()

    def test_require_tls_makes_plaintext_fail(self) -> None:
        client = WSClient(self.url, ConnectOptions(timeout=5))
        client.connect()
        checks = measure.health_checks(client, require_tls=True)
        status = {c.name: c.status for c in checks}["传输加密"]
        self.assertEqual(status, "fail")
        self.assertEqual(measure.worst_status(checks), "fail")
        client.close()

    def test_worst_status_ordering(self) -> None:
        checks = [measure.Check("a", "ok"), measure.Check("b", "warn")]
        self.assertEqual(measure.worst_status(checks), "warn")
        checks.append(measure.Check("c", "fail"))
        self.assertEqual(measure.worst_status(checks), "fail")


if __name__ == "__main__":
    unittest.main()
