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
# USER API TESTS
# ===========================================================================

class TestUserAPI:

    def setup_method(self):
        db = TestSession()
        db.query(User).delete(); db.commit(); db.close()

    def _logged_in_client(self, username="alice"):
        _make_user(username, "secret")
        c = TestClient(app)
        c.post("/login", data={"username": username, "password": "secret"})
        return c

    def test_get_user_returns_profile(self):
        c = self._logged_in_client()
        r = c.get("/api/user")
        assert r.status_code == 200
        data = r.json()
        assert data["username"] == "alice"
        assert "id" in data

    def test_get_user_unauthenticated(self):
        with TestClient(app) as c:
            r = c.get("/api/user")
        assert r.json().get("detail") == "Not authenticated"

    def test_update_user_email(self):
        c = self._logged_in_client()
        r = c.put("/api/user", json={"email": "alice@example.com"})
        assert r.status_code == 200
        # Verify persisted
        r2 = c.get("/api/user")
        assert r2.json()["email"] == "alice@example.com"

    def test_update_user_bio_and_age(self):
        c = self._logged_in_client()
        c.put("/api/user", json={"bio": "I fish.", "age": 30})
        r = c.get("/api/user")
        assert r.json()["bio"] == "I fish."
        assert r.json()["age"] == 30


# ===========================================================================
# ADMIN TESTS
# ===========================================================================

class TestAdmin:

    def setup_method(self):
        db = TestSession()
        db.query(User).delete(); db.commit(); db.close()

    def _admin_client(self):
        _make_user("admin_user", "adminpass", role="admin")
        c = TestClient(app)
        c.post("/admin/login", data={"username": "admin_user", "password": "adminpass"})
        return c

    def test_admin_login_success(self):
        _make_user("admin_user", "adminpass", role="admin")
        r = client.post("/admin/login",
                        data={"username": "admin_user", "password": "adminpass"},
                        follow_redirects=False)
        assert r.status_code == 302
        assert "/admin/dashboard" in r.headers["location"]

    def test_admin_login_non_admin_rejected(self):
        _make_user("regular", "pass", role="user")
        r = client.post("/admin/login",
                        data={"username": "regular", "password": "pass"},
                        follow_redirects=False)
        assert r.status_code == 302
        assert "/admin/login" in r.headers["location"]

    def test_get_all_users_as_admin(self):
        c = self._admin_client()
        _make_user("bob", "x")
        r = c.get("/api/admin/users")
        assert r.status_code == 200
        usernames = [u["username"] for u in r.json()["users"]]
        assert "admin_user" in usernames
        assert "bob" in usernames

    def test_get_all_users_unauthorized(self):
        with TestClient(app) as c:
            r = c.get("/api/admin/users")
        assert r.json().get("detail") == "Unauthorized"

    def test_admin_delete_regular_user(self):
        c    = self._admin_client()
        bob  = _make_user("bob", "x")
        r    = c.delete(f"/api/admin/users/{bob.id}")
        assert r.status_code == 200
        # Confirm gone
        users_r = c.get("/api/admin/users")
        ids = [u["id"] for u in users_r.json()["users"]]
        assert bob.id not in ids

    def test_admin_cannot_delete_admin(self):
        c = self._admin_client()
        db = TestSession()
        admin = db.query(User).filter(User.username == "admin_user").first()
        db.close()
        r = c.delete(f"/api/admin/users/{admin.id}")
        assert r.status_code == 200            # endpoint returns 200 with detail
        assert "Cannot delete admin" in r.json().get("detail", "")

    def test_admin_create_user(self):
        c = self._admin_client()
        r = c.post("/api/admin/create-user",
                   data={"username": "newguy", "password": "pw", "role": "user"})
        assert r.status_code == 200
        assert r.json()["message"] == "User created successfully"

    def test_admin_create_user_invalid_role(self):
        c = self._admin_client()
        r = c.post("/api/admin/create-user",
                   data={"username": "x", "password": "y", "role": "superadmin"})
        assert r.json().get("detail") == "Invalid role"

    def test_check_admin_flag(self):
        c = self._admin_client()
        r = c.get("/api/check-admin")
        assert r.json()["is_admin"] is True


