"""
test_ble_connect_action.py
==========================
Integration tests for sensor WebSocket relay behaviour.
Verifies that sensor_metrics sent by one client are broadcast to others.
"""

import os
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import json
import unittest
from fastapi.testclient import TestClient
import main


class TestSensorMetricsRelay(unittest.TestCase):

    def test_sensor_metrics_broadcast_to_other_clients(self):
        """A sensor_metrics message sent by one client is rebroadcast to others."""
        with TestClient(main.app) as client:
            with client.websocket_connect("/ws") as sender:
                with client.websocket_connect("/ws") as receiver:
                    sender.receive_text()   # init
                    receiver.receive_text() # init

                    sender.send_text(json.dumps({
                        "action": "sensor_metrics",
                        "active": True,
                        "speed_ms": 2.1,
                        "speed_kmh": 7.56,
                        "cadence_rpm": 60.0,
                        "distance_m": 21.0,
                        "distance_km": 0.021,
                    }))

                    state = json.loads(receiver.receive_text())
                    self.assertEqual(state["type"], "sensor_state")
                    self.assertTrue(state["active"])

                    metrics = json.loads(receiver.receive_text())
                    self.assertEqual(metrics["type"], "metrics")
                    self.assertAlmostEqual(metrics["speed_kmh"], 7.56)
                    self.assertAlmostEqual(metrics["cadence_rpm"], 60.0)
                    self.assertAlmostEqual(metrics["distance_m"], 21.0)

    def test_inactive_sensor_broadcasts_false(self):
        """active=False is relayed correctly."""
        with TestClient(main.app) as client:
            with client.websocket_connect("/ws") as sender:
                with client.websocket_connect("/ws") as receiver:
                    sender.receive_text()
                    receiver.receive_text()

                    sender.send_text(json.dumps({
                        "action": "sensor_metrics",
                        "active": False,
                        "speed_ms": 0,
                        "speed_kmh": 0,
                        "cadence_rpm": 0,
                        "distance_m": 0,
                        "distance_km": 0,
                    }))

                    state = json.loads(receiver.receive_text())
                    self.assertEqual(state["type"], "sensor_state")
                    self.assertFalse(state["active"])


if __name__ == "__main__":
    unittest.main()
