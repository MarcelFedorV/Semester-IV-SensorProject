"""
main.py — FastAPI server bridging BLE manager to browser.

pip install fastapi uvicorn bleak
python main.py  →  http://localhost:8000
"""
import os
import asyncio
import json
import sys
import random
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
import uvicorn
from fish_logic import pick_fish
from fish_data import FISH_BY_ID, FISH

from ble_client import BLEClient

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Depends, Form
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from passlib.context import CryptContext
from database import SessionLocal, engine, Base
from models import User
from fishing_models import FishCatch, FishCollection, AchievementUnlock
import fishing_db
import bcrypt
import uvicorn
from fish_data import FISH_BY_ID, FISH, LOCATIONS, MYSTERY_FISH_BY_LOCATION, LOCATIONS_BY_ID
from sensor_device import BLEManager
from achievements import ACHIEVEMENTS, ACHIEVEMENTS_BY_ID
from fish_agent import FishAgent




app = FastAPI()


if sys.platform == "win32":
    asyncio.set_event_loop(asyncio.SelectorEventLoop())

manager     = BLEClient()
connections: list[WebSocket] = []


async def broadcast(msg: dict):
    text = json.dumps(msg)
    dead = []
    for ws in connections:
        try:    await ws.send_text(text)
        except: dead.append(ws)
    for ws in dead:
        connections.remove(ws)

# Wire BLE events → WebSocket
manager.on_device_updated       = lambda d: asyncio.create_task(broadcast({"type": "device_updated",        "device":  d}))
manager.on_device_removed       = lambda a: asyncio.create_task(broadcast({"type": "device_removed",        "address": a}))
manager.on_scan_started         = lambda:   asyncio.create_task(broadcast({"type": "scan_started"}))
manager.on_scan_stopped         = lambda:   asyncio.create_task(broadcast({"type": "scan_stopped"}))
manager.on_connected            = lambda a: asyncio.create_task(broadcast({"type": "connected",             "address": a}))
manager.on_disconnected         = lambda a: asyncio.create_task(broadcast({"type": "disconnected",          "address": a}))
manager.on_error                = lambda m: asyncio.create_task(broadcast({"type": "error",                 "message": m}))
manager.on_interrogation_result = lambda r: asyncio.create_task(broadcast({"type": "interrogation_result", "result":  r}))
manager.on_switch_progress      = lambda m: asyncio.create_task(broadcast({"type": "switch_progress",       "message": m}))
manager.on_switch_done          = lambda r: asyncio.create_task(broadcast({"type": "switch_done",           "result":  r}))
manager.on_devices_list         = lambda l: asyncio.create_task(broadcast({"type": "devices_list", "devices": l}))
manager.on_status               = lambda s: asyncio.create_task(broadcast({"type": "status",       "status":  s}))
manager.on_sensor_state = lambda active: asyncio.create_task(broadcast({"type": "sensor_state", "active": active}))

def _on_metrics(m: dict):
    print(
        f"[Sensor] speed={m['speed_kmh']:5.1f} km/h  "
        f"cadence={m['cadence_rpm']:5.1f} rpm  "
        f"distance={m['distance_m']:6.1f} m"
    )
    asyncio.create_task(broadcast({"type": "metrics", **m}))

manager.on_metrics = _on_metrics


@asynccontextmanager
async def lifespan(app: FastAPI):
    await manager.connect_to_bridge()
    print("[Server] Ready at http://localhost:8000")
    yield
    await manager.disconnect()
    await manager.stop_scan()

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
        return response

app = FastAPI(lifespan=lifespan)

Base.metadata.create_all(bind=engine)
app.add_middleware(SessionMiddleware, secret_key="your-secret-key-change-this")

templates = Jinja2Templates(directory="pages")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- Auth helpers ---
def get_current_user(request: Request):
    return request.session.get("user")

def require_auth(request: Request):
    if not request.session.get("user"):
        return RedirectResponse("/login", status_code=302)
    return None

app.add_middleware(SecurityHeadersMiddleware)

@app.get("/")
async def serve_welcome(request: Request):
    if not request.session.get("user"):
        return RedirectResponse("/login", status_code=302)
    return FileResponse("pages/welcome.html")

@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse(request=request,
    name="login.html",
    context={"error": None})

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    db = SessionLocal()
    user = db.query(User).filter(User.username == username).first()
    db.close()
    if not user or not bcrypt.checkpw(password.encode("utf-8"), user.password.encode("utf-8")):
        return RedirectResponse("/login", status_code=302)
    request.session["user"] = user.username
    return RedirectResponse("/", status_code=302)

@app.post("/register")
async def register(request: Request, username: str = Form(...), password: str = Form(...)):
    db = SessionLocal()
    
    # Check if user already exists
    if db.query(User).filter(User.username == username).first():
        db.close()
        return {"detail": "Username already exists"}, 400
    
    # Hash password and create user
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    user = User(username=username, password=hashed.decode("utf-8"))
    db.add(user)
    db.commit()
    db.close()
    
    return {"message": "User created successfully"}

@app.get("/api/check-auth")
async def check_auth(request: Request):
    user = request.session.get("user")
    return {"authenticated": user is not None, "user": user}

@app.get("/account")
async def account_page(request: Request):
    if not request.session.get("user"):
        return RedirectResponse("/login", status_code=302)
    return FileResponse("pages/account.html")

@app.get("/api/user")
async def get_user(request: Request):
    username = request.session.get("user")
    if not username:
        return {"detail": "Not authenticated"}, 401
    
    db = SessionLocal()
    user = db.query(User).filter(User.username == username).first()
    db.close()
    
    if not user:
        return {"detail": "User not found"}, 404
    
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "bio": user.bio,
        "age": user.age,
        "favorite_game": user.favorite_game,
        "role": user.role,
        "language": user.language
    }

@app.put("/api/user")
async def update_user(request: Request):
    username = request.session.get("user")
    if not username:
        return {"detail": "Not authenticated"}, 401
    
    data = await request.json()
    print(f"Update data: {data}")
    db = SessionLocal()
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        db.close()
        return {"detail": "User not found"}, 404
    
    if "email" in data:
        user.email = data.get("email")
    if "bio" in data:
        user.bio = data.get("bio")
    if "age" in data:
        user.age = data.get("age")
    if "favorite_game" in data:
        user.favorite_game = data.get("favorite_game")
    if "language" in data:
        user.language = data.get("language")
    
    db.commit()
    db.close()
    
    return {"message": "User updated successfully"}

@app.get("/admin/login")
async def admin_login_page(request: Request):
    if request.session.get("admin"):
        return RedirectResponse("/admin/dashboard", status_code=302)
    return FileResponse("pages/admin_login.html")

@app.post("/admin/login")
async def admin_login(request: Request, username: str = Form(...), password: str = Form(...)):
    db = SessionLocal()
    user = db.query(User).filter(User.username == username).first()
    db.close()
    
    if not user or user.role != "admin" or not bcrypt.checkpw(password.encode("utf-8"), user.password.encode("utf-8")):
        return RedirectResponse("/admin/login", status_code=302)
    
    request.session["admin"] = user.username
    request.session["user"] = user.username
    return RedirectResponse("/admin/dashboard", status_code=302)

@app.get("/api/check-admin")
async def check_admin(request: Request):
    admin = request.session.get("admin")
    user = request.session.get("user")
    return {
        "authenticated": admin is not None,
        "is_admin": admin is not None,
        "user": user
    }

@app.get("/admin/dashboard")
async def admin_dashboard(request: Request):
    if not request.session.get("admin"):
        return RedirectResponse("/admin/login", status_code=302)
    return FileResponse("pages/admin_dashboard.html")

@app.get("/api/admin/users")
async def get_all_users(request: Request):
    if not request.session.get("admin"):
        return {"detail": "Unauthorized"}, 401
    
    db = SessionLocal()
    users = db.query(User).all()
    db.close()
    
    return {
        "users": [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "role": u.role
            }
            for u in users
        ]
    }

@app.post("/api/admin/create-user")
async def admin_create_user(request: Request, username: str = Form(...), password: str = Form(...), email: str = Form(None), role: str = Form("user")):
    if not request.session.get("admin"):
        return {"detail": "Unauthorized"}, 401
    
    # Validate role
    if role not in ["user", "admin"]:
        return {"detail": "Invalid role"}, 400
    
    db = SessionLocal()
    
    # Check if user already exists
    if db.query(User).filter(User.username == username).first():
        db.close()
        return {"detail": "Username already exists"}, 400
    
    # Hash password and create user
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    user = User(
        username=username,
        password=hashed.decode("utf-8"),
        email=email if email else None,
        role=role
    )
    db.add(user)
    db.commit()
    db.close()
    
    return {"message": "User created successfully"}

@app.delete("/api/admin/users/{user_id}")
async def admin_delete_user(request: Request, user_id: int):
    if not request.session.get("admin"):
        return {"detail": "Unauthorized"}, 401
    
    db = SessionLocal()
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        db.close()
        return {"detail": "User not found"}, 404
    
    # Prevent deleting admins
    if user.role == "admin":
        db.close()
        return {"detail": "Cannot delete admin users"}, 403
    
    db.delete(user)
    db.commit()
    db.close()
    
    return {"message": "User deleted successfully"}

@app.get("/admin/logout")
async def admin_logout(request: Request):
    request.session.clear()
    return RedirectResponse("/admin/login", status_code=302)

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=302)

@app.get("/ble")
async def serve_ble(request: Request):
    if not request.session.get("user"):
        return RedirectResponse("/login", status_code=302)
    return FileResponse("index.html")

@app.get("/developers")
async def serve_dev(request: Request):
    if not request.session.get("user"):
        return RedirectResponse("/login", status_code=302)
    return FileResponse("pages/developers.html")

@app.get("/frontpage")
async def serve_frontpage(request: Request):
    if not request.session.get("user"):
        return RedirectResponse("/login", status_code=302)
    return FileResponse("pages/frontpage.html")

@app.get("/metrics")
async def serve_metrics(request: Request):
    if not request.session.get("user"):
        return RedirectResponse("/login", status_code=302)
    return FileResponse("pages/metrics.html")

@app.get("/Start")
async def landing(request: Request):
    if not request.session.get("user"):
        return RedirectResponse("/login", status_code=302)
    return FileResponse("Start.html")

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    connections.append(ws)
    print(f"[WS] Browser connected ({len(connections)} total)")
    await ws.send_text(json.dumps({"type": "init"}))
    await manager.get_devices()  # result broadcasts via on_devices_list
    await manager.get_status()   # result broadcasts via on_status

    async def heartbeat():
        while True:
            await asyncio.sleep(30)
            try:
                await ws.send_text(json.dumps({"type": "ping"}))
            except Exception:
                break

    heartbeat_task = asyncio.create_task(heartbeat())
    
    try:
        while True:
            raw = await ws.receive_text()
            await handle_message(ws, json.loads(raw))
    except WebSocketDisconnect:
        pass
    finally:
        heartbeat_task.cancel()
        if ws in connections:
            connections.remove(ws)
        print(f"[WS] Browser disconnected ({len(connections)} total)")


async def handle_message(ws: WebSocket, msg: dict):
    action = msg.get("action")
    print(f"[WS] {msg}")

    if action == "scan":
        asyncio.create_task(manager.start_scan(duration=float(msg.get("duration", 8.0))))

    elif action == "scan_continuous":
        asyncio.create_task(manager.start_scan_continuous())

    elif action == "stop_scan":
        await manager.stop_scan()

    elif action == "clear":
        manager.clear_devices()
        await broadcast({"type": "cleared"})

    elif action == "connect":
        address = msg.get("address")
        if address:
            asyncio.create_task(manager.connect_and_interrogate(address))
            await broadcast({"type": "connecting", "address": address})

    elif action == "disconnect":
        await manager.disconnect()

    elif action == "mode_switch":
        address      = msg.get("address")
        current_mode = msg.get("current_mode")
        if address and current_mode:
            asyncio.create_task(manager.do_mode_switch(address, current_mode))




@app.get("/FishingGame")
async def serve_fishing_game(request: Request):
    if not request.session.get("user"):
        return RedirectResponse("/login", status_code=302)
    return FileResponse("games/FishingGame/index.html")

# Serve all other FishingGame assets without auth check
@app.get("/FishingGame/{path:path}")
async def serve_fishing_assets(path: str):
    file_path = f"games/FishingGame/{path}"
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return FileResponse("games/FishingGame/index.html")


@app.get("/index.js")
async def serve_js():
    return FileResponse("games/FishingGame/index.js")

@app.get("/index.wasm")
async def serve_wasm():
    return FileResponse("games/FishingGame/index.wasm")

@app.get("/index.pck")
async def serve_pck():
    return FileResponse("games/FishingGame/index.pck")

@app.get("/index.png")
async def serve_png():
    return FileResponse("games/FishingGame/index.png")

@app.get("/index.icon.png")
async def serve_icon():
    return FileResponse("games/FishingGame/index.icon.png")

@app.get("/index.audio.worklet.js")
async def serve_audio_worklet():
    return FileResponse("games/FishingGame/index.audio.worklet.js")

@app.get("/api/me")
async def get_me(request: Request):
    username = request.session.get("user")
    if not username:
        return {"detail": "Not authenticated"}, 401
    db = SessionLocal()
    user = db.query(User).filter(User.username == username).first()
    db.close()
    if not user:
        return {"detail": "Not found"}, 404
    return {"id": user.id, "username": user.username}

@app.post("/fish/catch")
async def catch_fish(depth: float, patient_id: int = 1, location_id: int = 1):
    db = SessionLocal()
    try:
        # Unified FishAgent system: each agent decides if it catches
        caught = fishing_db.get_caught_ids(db, patient_id)
        location_fish = [f for f in FISH if f["location_id"] == location_id]
        location_fish_ids = {f["id"] for f in location_fish}
        location_complete = location_fish_ids.issubset(caught) if location_fish_ids else False

        # Check if we should try a mystery fish
        use_mystery = location_complete and random.random() < 0.3
        if use_mystery:
            mystery = MYSTERY_FISH_BY_LOCATION.get(location_id)
            pool = [mystery] if mystery else location_fish
        else:
            pool = location_fish if location_fish else FISH

        # Try each fish in pool — first one that catches wins
        random.shuffle(pool)
        caught_fish = None
        for fish in pool:
            agent = FishAgent(fish)
            result = agent.run(depth, location_id)
            if result["caught"]:
                caught_fish = fish
                break

        if not caught_fish:
            return {
                "fish": None,
                "missed": True,
                "new_achievements": []
            }

        is_new = fishing_db.save_catch(db, patient_id, caught_fish["id"], location_id, depth)
        caught_after = fishing_db.get_caught_ids(db, patient_id)
        new_achievements = fishing_db.check_fishing_achievements(db, patient_id, caught_fish, caught_after)

        return {
            "fish": caught_fish,
            "new": is_new,
            "missed": False,
            "location_complete": location_complete,
            "new_achievements": [ACHIEVEMENTS_BY_ID[a] for a in new_achievements if a in ACHIEVEMENTS_BY_ID]
        }
    finally:
        db.close()

@app.get("/fish/collection/{patient_id}")
async def get_collection(patient_id: int):
    db = SessionLocal()
    try:
        caught = fishing_db.get_caught_ids(db, patient_id)
        collection = [
            {
                **f,
                "caught": f["id"] in caught,
                "location": LOCATIONS_BY_ID[f["location_id"]]["name"] if f["location_id"] in LOCATIONS_BY_ID else "Unknown"
            }
            for f in FISH
        ]

        mystery_entries = []
        for loc_id, mystery in MYSTERY_FISH_BY_LOCATION.items():
            location_fish = [f for f in FISH if f["location_id"] == loc_id]
            location_fish_ids = {f["id"] for f in location_fish}
            location_complete = location_fish_ids.issubset(caught) if location_fish_ids else False

            if location_complete:
                mystery_entries.append({
                    **mystery,
                    "caught": mystery["id"] in caught,
                    "location": LOCATIONS_BY_ID[loc_id]["name"]
                })
            else:
                mystery_entries.append({
                    "id": mystery["id"],
                    "name": "???",
                    "rarity": "Location Legend",
                    "location_id": loc_id,
                    "location": LOCATIONS_BY_ID[loc_id]["name"],
                    "color": "#333333",
                    "caught": False,
                    "locked": True
                })

        return {
            "collection": collection,
            "mystery_fish": mystery_entries
        }
    finally:
        db.close()

@app.get("/fish/location_complete/{patient_id}/{location_id}")
async def check_location_complete(patient_id: int, location_id: int):
    db = SessionLocal()
    try:
        caught = fishing_db.get_caught_ids(db, patient_id)
        location_fish = [f for f in FISH if f["location_id"] == location_id]
        location_fish_ids = {f["id"] for f in location_fish}
        all_caught = location_fish_ids.issubset(caught) if location_fish_ids else False
        mystery = MYSTERY_FISH_BY_LOCATION.get(location_id)
        mystery_unlocked = mystery and mystery["id"] in caught
        return {
            "complete": all_caught,
            "total": len(location_fish_ids),
            "caught": len(location_fish_ids.intersection(caught)),
            "mystery_unlocked": mystery_unlocked,
            "mystery_fish": mystery if all_caught else None
        }
    finally:
        db.close()




@app.post("/player/distance")
async def update_distance(request: Request, distance_m: float, user_id: int):
    """Called by WebSocket metrics handler to save distance."""
    db = SessionLocal()
    try:
        new_achievements = fishing_db.add_distance(db, user_id, distance_m)
        return {
            "stats": fishing_db.get_stats(db, user_id),
            "new_achievements": [ACHIEVEMENTS_BY_ID[a] for a in new_achievements if a in ACHIEVEMENTS_BY_ID]
        }
    finally:
        db.close()




@app.get("/player/stats/{user_id}")
async def get_player_stats(user_id: int):
    db = SessionLocal()
    try:
        unlocked_ids = fishing_db.get_unlocked_achievements(db, user_id)
        return {
            "stats":            fishing_db.get_stats(db, user_id),
            "achievements":     unlocked_ids,
            "all_achievements": ACHIEVEMENTS
        }
    finally:
        db.close()





@app.get("/locations")
async def get_locations():
    return {"locations": LOCATIONS}

print(f"[DEBUG] cwd: {os.getcwd()}")
print(f"[DEBUG] files in cwd: {os.listdir('.')}")
print(f"[DEBUG] game path exists: {os.path.exists('games/FishingGame/index.html')}")

if os.path.exists("games/FishingGame/index.html"):
    app.mount("/FishingGame", StaticFiles(directory="games/FishingGame", html=True), name="fishing")
if os.path.exists("games/FishingGame/index.html"):
    app.mount("/FishingGame", StaticFiles(directory="games/FishingGame", html=True), name="fishing")

app.mount("/style", StaticFiles(directory="pages/styles"), name="style")
app.mount("/languages", StaticFiles(directory="pages/languages"), name="languages")

if os.path.exists("../space-game/index.html"):
    app.mount("/SpaceFunk", StaticFiles(directory="../space-game", html=True), name="space")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
