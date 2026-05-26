import asyncio
import json
import time
import unittest

from fastapi.testclient import TestClient

import main


class FakeBLEClient:
    def __init__(self):
        self.is_bridge_connected = False
        self.scan_calls = []
        self.connect_calls = []
        self.disconnect_calls = 0
        self.stop_scan_calls = 0
        self.clear_calls = 0
        self.mode_switch_calls = []

        self.on_device_updated = lambda d: None
        self.on_device_removed = lambda a: None
        self.on_scan_started = lambda: None
        self.on_scan_stopped = lambda: None
        self.on_connected = lambda a: None
        self.on_disconnected = lambda a: None
        self.on_error = lambda m: None
        self.on_interrogation_result = lambda r: None
        self.on_switch_progress = lambda m: None
        self.on_switch_done = lambda r: None
        self.on_devices_list = lambda l: None
        self.on_status = lambda s: None
        self.on_bridge_connected = lambda: None
        self.on_bridge_disconnected = lambda: None
        self.on_sensor_state = lambda active: None
        self.on_metrics = lambda m: None

    async def connect_to_bridge(self):
        self.is_bridge_connected = True
        self.on_bridge_connected()

    async def close(self):
        self.is_bridge_connected = False
        self.on_bridge_disconnected()

    async def start_scan(self, duration=8.0):
        self.scan_calls.append(duration)

    async def start_scan_continuous(self):
        self.scan_calls.append("continuous")

    async def stop_scan(self):
        self.stop_scan_calls += 1

    def clear_devices(self):
        self.clear_calls += 1

    async def get_devices(self):
        self.on_devices_list([])

    async def get_status(self):
        self.on_status({
            "scanning": False,
            "connected": False,
            "connected_to": None,
            "device_count": 0,
        })

    async def connect_and_interrogate(self, address):
        self.connect_calls.append(address)
        self.on_connected(address)
        self.on_interrogation_result({
            "accepted": True,
            "address": address,
            "name": "Fake sensor",
            "mode": "speed",
            "location": "Unknown",
            "is_xoss": False,
            "features": [],
        })

    async def disconnect(self):
        self.disconnect_calls += 1
        self.on_disconnected("AA:BB:CC:DD:EE:FF")

    async def do_mode_switch(self, address, current_mode):
        self.mode_switch_calls.append((address, current_mode))
        self.on_switch_progress("switching")
        self.on_switch_done({"success": True})

    async def emit(self, event, payload=None):
        if event == "metrics":
            self.on_metrics(payload)
        elif event == "sensor_state":
            self.on_sensor_state(payload)
        elif event == "device_updated":
            self.on_device_updated(payload)
        await asyncio.sleep(0)


class TestBLEIntegration(unittest.TestCase):
    def tearDown(self):
        main.create_app()

    def test_websocket_broadcasts_fake_metrics(self):
        fake_ble = FakeBLEClient()
        main.create_app(fake_ble)

        with TestClient(main.app) as client:
            with client.websocket_connect("/ws") as websocket:
                initial = websocket.receive_text()
                self.assertEqual(json.loads(initial)["type"], "init")

                asyncio.run(fake_ble.emit("metrics", {
                    "speed_ms": 1.0,
                    "speed_kmh": 3.6,
                    "cadence_rpm": 60.0,
                    "distance_m": 10.0,
                    "distance_km": 0.01,
                }))

                time.sleep(0.05)
                payload = json.loads(websocket.receive_text())
                self.assertEqual(payload["type"], "metrics")
                self.assertEqual(payload["speed_kmh"], 3.6)
                self.assertEqual(payload["distance_m"], 10.0)

    def test_scan_action_calls_fake_ble_client(self):
        fake_ble = FakeBLEClient()
        main.create_app(fake_ble)

        with TestClient(main.app) as client:
            with client.websocket_connect("/ws") as websocket:
                websocket.receive_text()
                websocket.send_text(json.dumps({"action": "scan", "duration": 4.0}))

                time.sleep(0.1)
                self.assertEqual(fake_ble.scan_calls, [4.0])


if __name__ == "__main__":
    unittest.main()
