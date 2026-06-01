"""
test_ble_integration.py
=======================
Integration tests for WebSocket connection lifecycle and sensor relay.
"""

import os
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import json
import threading
import unittest
from fastapi.testclient import TestClient
import main


class TestWebSocketLifecycle(unittest.TestCase):

    def test_init_message_on_connect(self):
        """Server sends an init message immediately on WebSocket connect."""
        with TestClient(main.app) as client:
            with client.websocket_connect("/ws") as ws:
                msg = json.loads(ws.receive_text())
                self.assertEqual(msg["type"], "init")

    def test_multiple_clients_connect(self):
        """Multiple clients can connect simultaneously."""
        with TestClient(main.app) as client:
            with client.websocket_connect("/ws") as ws1:
                with client.websocket_connect("/ws") as ws2:
                    msg1 = json.loads(ws1.receive_text())
                    msg2 = json.loads(ws2.receive_text())
                    self.assertEqual(msg1["type"], "init")
                    self.assertEqual(msg2["type"], "init")


class TestSensorMetricsRelay(unittest.TestCase):

    def test_metrics_values_relayed_correctly(self):
        """All metric fields are passed through unchanged."""
        with TestClient(main.app) as client:
            with client.websocket_connect("/ws") as sender:
                with client.websocket_connect("/ws") as receiver:
                    sender.receive_text()
                    receiver.receive_text()

                    sender.send_text(json.dumps({
                        "action": "sensor_metrics",
                        "active": True,
                        "speed_ms": 5.833,
                        "speed_kmh": 21.0,
                        "cadence_rpm": 85.5,
                        "distance_m": 500.0,
                        "distance_km": 0.5,
                    }))

                    receiver.receive_text()  # sensor_state
                    metrics = json.loads(receiver.receive_text())

                    self.assertEqual(metrics["type"], "metrics")
                    self.assertAlmostEqual(metrics["speed_kmh"], 21.0)
                    self.assertAlmostEqual(metrics["cadence_rpm"], 85.5)
                    self.assertAlmostEqual(metrics["distance_m"], 500.0)
                    self.assertAlmostEqual(metrics["distance_km"], 0.5)

    def test_missing_fields_default_to_zero(self):
        """Missing metric fields default to 0 rather than crashing."""
        with TestClient(main.app) as client:
            with client.websocket_connect("/ws") as sender:
                with client.websocket_connect("/ws") as receiver:
                    sender.receive_text()
                    receiver.receive_text()

                    sender.send_text(json.dumps({"action": "sensor_metrics"}))

                    receiver.receive_text()  # sensor_state
                    metrics = json.loads(receiver.receive_text())

                    self.assertEqual(metrics["type"], "metrics")
                    self.assertEqual(metrics["speed_kmh"], 0)
                    self.assertEqual(metrics["cadence_rpm"], 0)
                    self.assertEqual(metrics["distance_m"], 0)

    def test_sender_receives_own_broadcast(self):
        """The sending client receives its own broadcast — broadcast() fans out to all connections."""
        with TestClient(main.app) as client:
            with client.websocket_connect("/ws") as sender:
                sender.receive_text()  # init

                sender.send_text(json.dumps({
                    "action": "sensor_metrics",
                    "active": True,
                    "speed_kmh": 10.0,
                    "speed_ms": 2.77,
                    "cadence_rpm": 70.0,
                    "distance_m": 100.0,
                    "distance_km": 0.1,
                }))

                received = []
                def try_receive():
                    try:
                        received.append(sender.receive_text())
                    except Exception:
                        pass

                t = threading.Thread(target=try_receive)
                t.start()
                t.join(timeout=0.3)
                self.assertGreaterEqual(len(received), 1)  # at least sensor_state arrives


if __name__ == "__main__":
    unittest.main()
