"""
main_tests_1.py — Unit & integration tests for main.py

Requirements:
    pip install pytest httpx fastapi sqlalchemy passlib bcrypt


How to run the tests:

First, start containerization:
    docker-compose up --build

Then enter container 'backend':
    docker exec -it backend /bin/bash   

When in the container (!), run:
    python -m pytest unit_tests/main_tests_1.py -v

"""

import sys
import os
import types
import pytest
import bcrypt
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

# sys.path.insert(0, "/app")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# Stub helpers — must happen before importing main
# ---------------------------------------------------------------------------

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

# Fish stubs
FAKE_FISH = [
    {"id": 1, "name": "Goldfish",  "rarity": "Common",   "location_id": 1, "color": "#FFD700", "min_depth": 0,  "max_depth": 5},
    {"id": 2, "name": "Tuna",      "rarity": "Uncommon", "location_id": 1, "color": "#4169E1", "min_depth": 5,  "max_depth": 15},
    {"id": 3, "name": "Swordfish", "rarity": "Rare",     "location_id": 2, "color": "#C0C0C0", "min_depth": 10, "max_depth": 30},
]
FAKE_FISH_BY_ID      = {f["id"]: f for f in FAKE_FISH}
FAKE_LOCATIONS       = [{"id": 1, "name": "Lake"}, {"id": 2, "name": "Ocean"}]
FAKE_LOCATIONS_BY_ID = {loc["id"]: loc for loc in FAKE_LOCATIONS}
FAKE_MYSTERY         = {1: {"id": 99, "name": "Kraken", "rarity": "Legendary", "location_id": 1, "color": "#800080"}}

_stub_module("fish_logic", pick_fish=lambda depth, loc_id: FAKE_FISH[0])
_stub_module("fish_data",
    FISH=FAKE_FISH, FISH_BY_ID=FAKE_FISH_BY_ID,
    LOCATIONS=FAKE_LOCATIONS, LOCATIONS_BY_ID=FAKE_LOCATIONS_BY_ID,
    MYSTERY_FISH_BY_LOCATION=FAKE_MYSTERY,
)

fishing_models_mod = _stub_module("fishing_models")
fishing_models_mod.FishCatch      = MagicMock()
fishing_models_mod.FishCollection = MagicMock()
fishing_models_mod.Achievement    = MagicMock()

fishing_db_mod = _stub_module("fishing_db")
fishing_db_mod.get_caught_ids = MagicMock(return_value=set())
fishing_db_mod.save_catch     = MagicMock(return_value=True)

# ---------------------------------------------------------------------------
# In-memory SQLite database
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id            = Column(Integer, primary_key=True, index=True)
    username      = Column(String, unique=True, index=True, nullable=False)
    password      = Column(String, nullable=False)
    email         = Column(String, nullable=True)
    bio           = Column(String, nullable=True)
    age           = Column(Integer, nullable=True)
    favorite_game = Column(String, nullable=True)
    role          = Column(String, default="user")

TEST_ENGINE = create_engine("sqlite:////tmp/test.db", connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=TEST_ENGINE)

# Register stubs before main is imported
_stub_module("database", SessionLocal=TestSession, engine=TEST_ENGINE, Base=Base)
_stub_module("models", User=User)

Base.metadata.create_all(bind=TEST_ENGINE)

# ---------------------------------------------------------------------------
# Import app — stubs are already in sys.modules
# ---------------------------------------------------------------------------

from main import app  # noqa: E402

# ---------------------------------------------------------------------------
# Patch main's local name bindings for the entire test session.
# "from database import SessionLocal" in main.py creates a local binding
# that survives module-level assignment, so we use patch().start() to
# intercept every call for the full process lifetime.
# ---------------------------------------------------------------------------

_patcher_session = patch("main.SessionLocal", TestSession)
_patcher_user    = patch("main.User", User)
_patcher_session.start()
_patcher_user.start()

# ---------------------------------------------------------------------------
# Shared test client
# ---------------------------------------------------------------------------

client = TestClient(app, raise_server_exceptions=True)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(username="alice", password="secret", role="user"):
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    db = TestSession()
    u  = User(username=username, password=hashed, role=role)
    db.add(u)
    db.commit()
    db.refresh(u)
    db.close()
    return u

def _reset_db():
    Base.metadata.drop_all(bind=TEST_ENGINE)
    Base.metadata.create_all(bind=TEST_ENGINE)


# ===========================================================================
# AUTH TESTS
# ===========================================================================

class TestAuth:

    def setup_method(self):
        from sqlalchemy import inspect, text
        import main as m
        print(f"\nSessionLocal same? {m.SessionLocal is TestSession}")
        _reset_db()
        tables = inspect(TEST_ENGINE).get_table_names()
        print(f"Tables after reset: {tables}")
        # Try a raw query directly
        with TEST_ENGINE.connect() as conn:
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            print(f"SQLite master tables: {result.fetchall()}")

    def test_register_new_user(self):
        r = client.post("/register", data={"username": "bob", "password": "pass123"})
        assert r.status_code == 200
        assert r.json().get("message") == "User created successfully"

    def test_register_duplicate_username(self):
        _make_user("bob")
        r = client.post("/register", data={"username": "bob", "password": "other"})
        # endpoint returns a tuple (dict, 400) which FastAPI serializes as a list
        body = r.json()
        if isinstance(body, list):
            assert body[1] == 400
        else:
            assert "detail" in body

    def test_login_success_redirects(self):
        _make_user("alice", "secret")
        r = client.post("/login", data={"username": "alice", "password": "secret"},
                        follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "/"

    def test_login_wrong_password_redirects_to_login(self):
        _make_user("alice", "secret")
        r = client.post("/login", data={"username": "alice", "password": "wrong"},
                        follow_redirects=False)
        assert r.status_code == 302
        assert "/login" in r.headers["location"]

    def test_login_unknown_user(self):
        r = client.post("/login", data={"username": "ghost", "password": "x"},
                        follow_redirects=False)
        assert r.status_code == 302
        assert "/login" in r.headers["location"]

    def test_logout_clears_session(self):
        _make_user("alice", "secret")
        client.post("/login", data={"username": "alice", "password": "secret"})
        r = client.get("/logout", follow_redirects=False)
        assert r.status_code == 302
        r2 = client.get("/", follow_redirects=False)
        assert "/login" in r2.headers["location"]

    def test_check_auth_unauthenticated(self):
        with TestClient(app) as c:
            r = c.get("/api/check-auth")
        assert r.json()["authenticated"] is False

    def test_check_auth_authenticated(self):
        _make_user("alice", "secret")
        with TestClient(app) as c:
            c.post("/login", data={"username": "alice", "password": "secret"})
            r = c.get("/api/check-auth")
        assert r.json()["authenticated"] is True
        assert r.json()["user"] == "alice"


# ===========================================================================
# USER API TESTS
# ===========================================================================

class TestUserAPI:

    def setup_method(self):
        _reset_db()

    def _logged_in_client(self, username="alice"):
        _make_user(username, "secret")
        c = TestClient(app)
        c.post("/login", data={"username": username, "password": "secret"})
        return c

    def test_get_user_returns_profile(self):
        c = self._logged_in_client()
        r = c.get("/api/user")
        assert r.status_code == 200
        assert r.json()["username"] == "alice"
        assert "id" in r.json()

    def test_get_user_unauthenticated(self):
        with TestClient(app) as c:
            r = c.get("/api/user")
        body = r.json()
        detail = body[0]["detail"] if isinstance(body, list) else body.get("detail")
        assert detail == "Not authenticated"

    def test_update_user_email(self):
        c = self._logged_in_client()
        r = c.put("/api/user", json={"email": "alice@example.com"})
        assert r.status_code == 200
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
        _reset_db()

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
        body = r.json()
        detail = body[0]["detail"] if isinstance(body, list) else body.get("detail")
        assert detail == "Unauthorized"

    def test_admin_delete_regular_user(self):
        c   = self._admin_client()
        bob = _make_user("bob", "x")
        r   = c.delete(f"/api/admin/users/{bob.id}")
        assert r.status_code == 200
        ids = [u["id"] for u in c.get("/api/admin/users").json()["users"]]
        assert bob.id not in ids

    def test_admin_cannot_delete_admin(self):
        c     = self._admin_client()
        db    = TestSession()
        admin = db.query(User).filter(User.username == "admin_user").first()
        db.close()
        r = c.delete(f"/api/admin/users/{admin.id}")
        body = r.json()
        detail = body[0]["detail"] if isinstance(body, list) else body.get("detail")
        assert "Cannot delete admin" in detail


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
        body = r.json()
        detail = body[0]["detail"] if isinstance(body, list) else body.get("detail")
        assert detail == "Invalid role"

    def test_check_admin_flag(self):
        c = self._admin_client()
        r = c.get("/api/check-admin")
        assert r.json()["is_admin"] is True


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

    def test_collection_includes_all_fish(self):
        r = client.get("/fish/collection/1")
        assert r.status_code == 200
        body = r.json()
        assert "collection"   in body
        assert "mystery_fish" in body
        names = [f["name"] for f in body["collection"]]
        assert "Goldfish" in names

    def test_collection_marks_caught_fish(self):
        fishing_db_mod.get_caught_ids.return_value = {1}
        r = client.get("/fish/collection/1")
        goldfish = next(f for f in r.json()["collection"] if f["id"] == 1)
        assert goldfish["caught"] is True

    def test_mystery_fish_locked_when_location_incomplete(self):
        fishing_db_mod.get_caught_ids.return_value = set()
        r = client.get("/fish/collection/1")
        loc1_mystery = next(m for m in r.json()["mystery_fish"] if m["location_id"] == 1)
        assert loc1_mystery["name"] == "???"
        assert loc1_mystery.get("locked") is True

    def test_mystery_fish_unlocked_when_location_complete(self):
        loc1_ids = {f["id"] for f in FAKE_FISH if f["location_id"] == 1}
        fishing_db_mod.get_caught_ids.return_value = loc1_ids
        r = client.get("/fish/collection/1")
        loc1_mystery = next(m for m in r.json()["mystery_fish"] if m["location_id"] == 1)
        assert loc1_mystery["name"] == "Kraken"

    def test_location_complete_endpoint_false(self):
        fishing_db_mod.get_caught_ids.return_value = set()
        r = client.get("/fish/location_complete/1/1")
        body = r.json()
        assert body["complete"] is False
        assert body["total"] == 2  # Goldfish + Tuna in location 1

    def test_location_complete_endpoint_true(self):
        loc1_ids = {f["id"] for f in FAKE_FISH if f["location_id"] == 1}
        fishing_db_mod.get_caught_ids.return_value = loc1_ids
        r = client.get("/fish/location_complete/1/1")
        assert r.json()["complete"] is True

    def test_get_locations(self):
        r = client.get("/locations")
        assert r.status_code == 200
        assert any(loc["name"] == "Lake" for loc in r.json()["locations"])


# ===========================================================================
# ROUTING TESTS
# ===========================================================================

class TestRouting:

    def setup_method(self):
        _reset_db()

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
        body = r.json()
        detail = body[0]["detail"] if isinstance(body, list) else body.get("detail")
        assert detail == "Not authenticated"