import unittest
import sys
import types
from fastapi.testclient import TestClient

# Provide a dummy ble_client module so importing backend.main doesn't fail in tests
ble_mod = types.ModuleType('ble_client')
class DummyBLEClient:
    def __init__(self, *a, **k):
        self.on_metrics = None
        self.is_bridge_connected = False
    async def connect_to_bridge(self):
        return
    async def disconnect(self):
        return
    async def stop_scan(self):
        return
ble_mod.BLEClient = DummyBLEClient
sys.modules['ble_client'] = ble_mod

# Provide a dummy sensor_device module with BLEManager used by backend.main
sensor_mod = types.ModuleType('sensor_device')
class DummyBLEManager:
    def __init__(self, *a, **k):
        pass
sensor_mod.BLEManager = DummyBLEManager
sys.modules['sensor_device'] = sensor_mod

import os
_orig_cwd = os.getcwd()
try:
    os.chdir(os.path.join(_orig_cwd, 'backend'))
    from backend.main import app
finally:
    os.chdir(_orig_cwd)

client = TestClient(app)

# Ensure relative static/template paths resolve during TestClient requests
os.chdir(os.path.join(_orig_cwd, 'backend'))

class TestWebEndpoints(unittest.TestCase):

    def test_metrics_page_served(self):
        # Unauthenticated requests should redirect to /login
        resp = client.get("/metrics", follow_redirects=False)
        self.assertIn(resp.status_code, (302, 307))
        self.assertIn('/login', resp.headers.get('location', ''))

    def test_metrics_script_available(self):
        resp = client.get('/scripts/metrics.js')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('loadGlobalStats', resp.text)

    def test_locations_endpoint(self):
        resp = client.get('/locations')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('locations', data)
        self.assertIsInstance(data['locations'], list)

    def test_stats_me_unauthorized(self):
        # Unauthenticated request to /api/stats/me should return 401
        resp = client.get('/api/stats/me')
        self.assertEqual(resp.status_code, 401)

    def test_stats_global_endpoint(self):
        # GET /api/stats/global should return 200 with a list
        resp = client.get('/api/stats/global')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsInstance(data, list)

    def test_protected_pages_redirect_to_login(self):
        # Verify protected pages redirect unauthenticated users to /login
        protected_paths = ['/games', '/spacefunk', '/fishinggame', '/developers']
        for path in protected_paths:
            resp = client.get(path, follow_redirects=False)
            self.assertIn(resp.status_code, (302, 307))
            self.assertIn('/login', resp.headers.get('location', ''))

if __name__ == '__main__':
    unittest.main(verbosity=2)
