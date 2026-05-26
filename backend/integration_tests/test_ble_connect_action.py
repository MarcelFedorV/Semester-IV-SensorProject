import json
import time
import unittest

from fastapi.testclient import TestClient

import main


class FakeBLEClient:
    def __init__(self):
        self.is_bridge_connected = False
        self.connect_calls = []
        self.on_connected = lambda a: None
        self.on_interrogation_result = lambda r: None

    async def connect_to_bridge(self):
        self.is_bridge_connected = True

    async def close(self):
        self.is_bridge_connected = False

    async def start_scan(self, duration=8.0):
        pass

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
        pass


class TestBLEConnectAction(unittest.TestCase):
    def tearDown(self):
        main.create_app()

    def test_connect_action_broadcasts_connecting(self):
        fake_ble = FakeBLEClient()
        main.create_app(fake_ble)

        with TestClient(main.app) as client:
            with client.websocket_connect("/ws") as websocket:
                websocket.receive_text()  # init

                websocket.send_text(json.dumps({
                    "action": "connect",
                    "address": "AA:BB:CC:DD:EE:FF",
                }))

                time.sleep(0.1)
                self.assertEqual(fake_ble.connect_calls, ["AA:BB:CC:DD:EE:FF"])

                payload = json.loads(websocket.receive_text())
                self.assertEqual(payload["type"], "connecting")
                self.assertEqual(payload["address"], "AA:BB:CC:DD:EE:FF")


if __name__ == "__main__":
    unittest.main()
