"""WSLens 作为 Python 库的三种典型用法（零第三方依赖）。

运行：python examples/library_usage.py
"""

from wslens.client import WSClient, ConnectOptions
from wslens.echod import EchoConfig, start_background_server
from wslens import measure


def demo_local() -> None:
    """① 完全离线：用内置回显服务器跑一遍完整链路。"""
    server = start_background_server("127.0.0.1", 0, EchoConfig(prefix="echo: "))
    try:
        with WSClient(server.url, ConnectOptions(timeout=5)) as ws:
            print("握手状态:", ws.handshake.status_code)
            ws.send_text("hello")
            print("回显:", ws.recv_message(timeout=5).text)
            print("心跳 RTT:", round(ws.ping(), 3), "ms")

            stats = measure.measure_ping(ws, count=5, interval=0.05)
            print("P95:", stats.p95_ms, "ms | 丢包:", stats.loss_pct, "%")

            for check in measure.health_checks(ws):
                print(f"  {check.icon} {check.name}: {check.detail}")
    finally:
        server.shutdown()
        server.server_close()


def demo_public() -> None:
    """② 公网端点：带自定义请求头与子协议。"""
    options = ConnectOptions(
        timeout=8,
        extra_headers={"X-Trace-Id": "wslens-demo"},
        subprotocols=["echo"],
    )
    with WSClient("wss://ws.postman-echo.com/raw", options) as ws:
        ws.send_text("hello from WSLens")
        print("公网回显:", ws.recv_message(timeout=8).text)


def demo_stats_only() -> None:
    """③ 只要统计数据：直接构造统计对象，不发起任何连接。"""
    stats = measure.PingStats(rtts=[12.0, 15.0, 9.0, 40.0, 11.0], sent=5)
    print("avg:", stats.avg_ms, "| P95:", stats.p95_ms, "| jitter:", stats.jitter_ms)


if __name__ == "__main__":
    print("=== ① 离线链路 ===")
    demo_local()
    print("\n=== ③ 纯统计 ===")
    demo_stats_only()
    print("\n（② 公网示例需要外网，可手动调用 demo_public()）")
