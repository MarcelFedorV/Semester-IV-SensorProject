"""
test_main.py — Unit & integration tests for main.py

Requirements:
    pip install pytest pytest-asyncio httpx fastapi sqlalchemy passlib bcrypt

Run:
    pytest test_main.py -v
"""

import pytest
import bcrypt
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ---------------------------------------------------------------------------
# Minimal stubs so main.py can be imported without real BLE / Godot assets
# ---------------------------------------------------------------------------

import sys, types

def _stub_module(name, **attrs):
    mod = types.ModuleType(name)
    mod.__dict__.update(attrs)
    sys.modules[name] = mod
    return mod

# BLE stub
ble_mod = _stub_module("ble_client")
class _FakeBLEClient:
    on_device_updated = on_device_removed = on_scan_started = on_scan_stopped = None
    on_connected = on_disconnected = on_error = on_interrogation_result = None
    on_switch_progress = on_switch_done = on_devices_list = on_status = None
    async def connect_to_bridge(self): pass
    async def disconnect(self): pass
    async def stop_scan(self): pass
    async def get_devices(self): pass
    async def get_status(self): pass
ble_mod.BLEClient = _FakeBLEClient

# fish_logic / fish_data stubs
FAKE_FISH = [
    {"id": 1, "name": "Goldfish",  "rarity": "Common",   "location_id": 1, "color": "#FFD700", "min_depth": 0,  "max_depth": 5},
    {"id": 2, "name": "Tuna",      "rarity": "Uncommon", "location_id": 1, "color": "#4169E1", "min_depth": 5,  "max_depth": 15},
    {"id": 3, "name": "Swordfish", "rarity": "Rare",     "location_id": 2, "color": "#C0C0C0", "min_depth": 10, "max_depth": 30},
]
FAKE_FISH_BY_ID   = {f["id"]: f for f in FAKE_FISH}
FAKE_LOCATIONS    = [{"id": 1, "name": "Lake"}, {"id": 2, "name": "Ocean"}]
FAKE_LOCATIONS_BY_ID = {loc["id"]: loc for loc in FAKE_LOCATIONS}
FAKE_MYSTERY      = {1: {"id": 99, "name": "Kraken", "rarity": "Legendary", "location_id": 1, "color": "#800080"}}

_stub_module("fish_logic",  pick_fish=lambda depth, loc_id: FAKE_FISH[0])
_stub_module("fish_data",
    FISH=FAKE_FISH, FISH_BY_ID=FAKE_FISH_BY_ID,
    LOCATIONS=FAKE_LOCATIONS, LOCATIONS_BY_ID=FAKE_LOCATIONS_BY_ID,
    MYSTERY_FISH_BY_LOCATION=FAKE_MYSTERY,
)

# fishing_models stub
fishing_models = _stub_module("fishing_models")
fishing_models.FishCatch     = MagicMock()
fishing_models.FishCollection = MagicMock()
fishing_models.Achievement   = MagicMock()

# fishing_db stub
fishing_db_mod = _stub_module("fishing_db")
fishing_db_mod.get_caught_ids = MagicMock(return_value=set())
fishing_db_mod.save_catch     = MagicMock(return_value=True)

# ---------------------------------------------------------------------------
# In-memory SQLite DB replacing the real one
# ---------------------------------------------------------------------------

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id       = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    email    = Column(String, nullable=True)
    bio      = Column(String, nullable=True)
    age      = Column(Integer, nullable=True)
    favorite_game = Column(String, nullable=True)
    role     = Column(String, default="user")

TEST_ENGINE   = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestSession   = sessionmaker(bind=TEST_ENGINE)

database_mod  = _stub_module("database",
    SessionLocal=TestSession, engine=TEST_ENGINE, Base=Base)
models_mod    = _stub_module("models", User=User)

Base.metadata.create_all(bind=TEST_ENGINE)

# ---------------------------------------------------------------------------
# Now we can safely import the app
# ---------------------------------------------------------------------------

from main import app  # noqa: E402  (must come after stubs)

client = TestClient(app, raise_server_exceptions=True)


# ===========================================================================
# FISHING API TESTS
# ===========================================================================

class TestFishingAPI:

    def setup_method(self):
        fishing_db_mod.get_caught_ids.reset_mock(return_value=True)
        fishing_db_mod.save_catch.reset_mock(return_value=True)
        fishing_db_mod.get_caught_ids.return_value = set()
        fishing_db_mod.save_catch.return_value     = True

    def test_catch_fish_returns_fish_and_new_flag(self):
        r = client.post("/fish/catch?depth=3.0&patient_id=1&location_id=1")
        assert r.status_code == 200
        body = r.json()
        assert "fish" in body
        assert "new"  in body
        assert body["fish"]["name"] == "Goldfish"
        assert body["new"] is True

    def test_catch_fish_not_new_when_already_caught(self):
        fishing_db_mod.save_catch.return_value = False
        r = client.post("/fish/catch?depth=3.0&patient_id=1&location_id=1")
        assert r.json()["new"] is False

    def test_mystery_fish_appears_when_location_complete(self):
        # All location-1 fish already caught
        loc1_ids = {f["id"] for f in FAKE_FISH if f["location_id"] == 1}
        fishing_db_mod.get_caught_ids.return_value = loc1_ids
        with patch("random.random", return_value=0.1):   # < 0.3 → mystery branch
            with patch("fish_logic.pick_fish", return_value=FAKE_MYSTERY[1]):
                r = client.post("/fish/catch?depth=3.0&patient_id=1&location_id=1")
        assert r.status_code == 200

    def test_collection_includes_all_fish(self):
        r = client.get("/fish/collection/1")
        assert r.status_code == 200
        body = r.json()
        assert "collection"  in body
        assert "mystery_fish" in body
        names = [f["name"] for f in body["collection"]]
        assert "Goldfish" in names

    def test_collection_marks_caught_fish(self):
        fishing_db_mod.get_caught_ids.return_value = {1}
        r = client.get("/fish/collection/1")
        collection = r.json()["collection"]
        goldfish = next(f for f in collection if f["id"] == 1)
        assert goldfish["caught"] is True

    def test_mystery_fish_locked_when_location_incomplete(self):
        fishing_db_mod.get_caught_ids.return_value = set()
        r = client.get("/fish/collection/1")
        mystery = r.json()["mystery_fish"]
        loc1_mystery = next(m for m in mystery if m["location_id"] == 1)
        assert loc1_mystery["name"] == "???"
        assert loc1_mystery.get("locked") is True

    def test_mystery_fish_unlocked_when_location_complete(self):
        loc1_ids = {f["id"] for f in FAKE_FISH if f["location_id"] == 1}
        fishing_db_mod.get_caught_ids.return_value = loc1_ids
        r = client.get("/fish/collection/1")
        mystery = r.json()["mystery_fish"]
        loc1_mystery = next(m for m in mystery if m["location_id"] == 1)
        assert loc1_mystery["name"] == "Kraken"

    def test_location_complete_endpoint_false(self):
        fishing_db_mod.get_caught_ids.return_value = set()
        r = client.get("/fish/location_complete/1/1")
        body = r.json()
        assert body["complete"] is False
        assert body["total"] == 2   # Goldfish + Tuna in location 1

    def test_location_complete_endpoint_true(self):
        loc1_ids = {f["id"] for f in FAKE_FISH if f["location_id"] == 1}
        fishing_db_mod.get_caught_ids.return_value = loc1_ids
        r = client.get("/fish/location_complete/1/1")
        assert r.json()["complete"] is True

    def test_get_locations(self):
        r = client.get("/locations")
        assert r.status_code == 200
        locs = r.json()["locations"]
        assert any(loc["name"] == "Lake" for loc in locs)


# ===========================================================================
# PAGE / ROUTING TESTS
# ===========================================================================

class TestRouting:

    def setup_method(self):
        db = TestSession()
        db.query(User).delete(); db.commit(); db.close()

    def _logged_in(self):
        _make_user("alice", "secret")
        c = TestClient(app)
        c.post("/login", data={"username": "alice", "password": "secret"})
        return c

    def test_root_redirects_unauthenticated(self):
        with TestClient(app) as c:
            r = c.get("/", follow_redirects=False)
        assert r.status_code == 302
        assert "/login" in r.headers["location"]

    def test_get_me_returns_user(self):
        c = self._logged_in()
        r = c.get("/api/me")
        assert r.status_code == 200
        assert r.json()["username"] == "alice"

    def test_get_me_unauthenticated(self):
        with TestClient(app) as c:
            r = c.get("/api/me")
        assert r.json().get("detail") == "Not authenticated"
        