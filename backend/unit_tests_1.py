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
    id            = Column(Integer, primary_key=True, index=True)
    username      = Column(String, unique=True, index=True, nullable=False)
    password      = Column(String, nullable=False)
    email         = Column(String, nullable=True)
    bio           = Column(String, nullable=True)
    age           = Column(Integer, nullable=True)
    favorite_game = Column(String, nullable=True)
    role          = Column(String, default="user")

TEST_ENGINE = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=TEST_ENGINE)

_stub_module("database", SessionLocal=TestSession, engine=TEST_ENGINE, Base=Base)
_stub_module("models", User=User)

Base.metadata.create_all(bind=TEST_ENGINE)

# ---------------------------------------------------------------------------
# Now we can safely import the app
# ---------------------------------------------------------------------------

from main import app  # stubs are in sys.modules, so main picks them up

# ---------------------------------------------------------------------------
# Keep SessionLocal and User patched for the entire test session
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True, scope="session")
def patch_db():
    with patch("main.SessionLocal", TestSession), \
         patch("main.User", User):
        yield

client = TestClient(app, raise_server_exceptions=True)

# ---------------------------------------------------------------------------
# Now we can safely import the app
# ---------------------------------------------------------------------------

from unittest.mock import patch

# Patch the names as they are bound INSIDE main.py
with patch("main.SessionLocal", TestSession), \
     patch("main.User", User):
    Base.metadata.create_all(bind=TEST_ENGINE)
    from main import app


import pytest
from unittest.mock import patch

@pytest.fixture(autouse=True, scope="session")
def patch_db():
    with patch("main.SessionLocal", TestSession), \
         patch("main.User", User):
        Base.metadata.create_all(bind=TEST_ENGINE)
        yield

client = TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(username="alice", password="secret", role="user"):
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    db = TestSession()
    u  = User(username=username, password=hashed, role=role)
    db.add(u); db.commit(); db.refresh(u); db.close()
    return u

def _auth_session(username="alice", password="secret"):
    """Login and return a session-carrying client."""
    client.post("/login", data={"username": username, "password": password})
    return client


# ===========================================================================
# AUTH TESTS
# ===========================================================================

class TestAuth:

    def setup_method(self):
        # Clear users between tests
        db = TestSession()
        db.query(User).delete(); db.commit(); db.close()

    # --- /register ---





    def test_debug_db(self):  # ← needs self
        from sqlalchemy import inspect
        import main as main_module
        
        print(f"\nmain.SessionLocal: {main_module.SessionLocal}")
        print(f"TestSession: {TestSession}")
        print(f"Same? {main_module.SessionLocal is TestSession}")
        
        inspector = inspect(TEST_ENGINE)
        print(f"Tables in TEST_ENGINE: {inspector.get_table_names()}")
        
        session = main_module.SessionLocal()
        print(f"Session bind: {session.bind}")
        session.close()





    def test_register_new_user(self):
        r = client.post("/register", data={"username": "bob", "password": "pass123"})
        assert r.status_code == 200
        assert r.json().get("message") == "User created successfully"

    def test_register_duplicate_username(self):
        _make_user("bob")
        r = client.post("/register", data={"username": "bob", "password": "other"})
        # endpoint returns a tuple (dict, 400) — FastAPI sends 200 with dict body
        # confirm the error key is present
        assert "detail" in r.json() or r.status_code == 400

    # --- /login ---

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

    # --- /logout ---

    def test_logout_clears_session(self):
        _make_user("alice", "secret")
        client.post("/login", data={"username": "alice", "password": "secret"})
        r = client.get("/logout", follow_redirects=False)
        assert r.status_code == 302
        # After logout, / should redirect to /login
        r2 = client.get("/", follow_redirects=False)
        assert "/login" in r2.headers["location"]

    # --- /api/check-auth ---

    def test_check_auth_unauthenticated(self):
        with TestClient(app) as c:   # fresh client = no session
            r = c.get("/api/check-auth")
        assert r.json()["authenticated"] is False

    def test_check_auth_authenticated(self):
        _make_user("alice", "secret")
        with TestClient(app) as c:
            c.post("/login", data={"username": "alice", "password": "secret"})
            r = c.get("/api/check-auth")
        assert r.json()["authenticated"] is True
        assert r.json()["user"] == "alice"


