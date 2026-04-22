"""
main.py — FastAPI server bridging BLE manager to browser.

pip install fastapi uvicorn bleak
python main.py  →  http://localhost:8000
"""
import os
import asyncio
import json
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
import uvicorn
from fish_logic import pick_fish
from fish_data import FISH_BY_ID, FISH

from ble_manager import BLEManager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Depends, Form
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from passlib.context import CryptContext
from database import SessionLocal, engine, Base
from models import User
import bcrypt

app = FastAPI()


if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

manager     = BLEManager()
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


@asynccontextmanager
async def lifespan(app: FastAPI):
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
        "role": user.role
    }

@app.put("/api/user")
async def update_user(request: Request):
    username = request.session.get("user")
    if not username:
        return {"detail": "Not authenticated"}, 401
    
    data = await request.json()
    
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
    await ws.send_text(json.dumps({
        "type":    "init",
        "devices": manager.get_devices(),
        "status":  manager.get_status(),
    }))

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



# Temporary in-memory storage until DB is set up
# key: patient_id, value: set of fish ids caught
caught_collection = {}

@app.post("/fish/catch")
async def catch_fish(depth: float, patient_id: int = 1):
    """Called by Godot when a fish is caught."""
    fish = pick_fish(depth)
    
    # Add to collection
    if patient_id not in caught_collection:
        caught_collection[patient_id] = set()
    caught_collection[patient_id].add(fish["id"])
    
    return {
        "fish": fish,
        "new": fish["id"] not in caught_collection.get(patient_id, set())
    }

@app.get("/fish/collection/{patient_id}")
async def get_collection(patient_id: int):
    """Returns full fish list with caught/uncaught status."""
    caught = caught_collection.get(patient_id, set())
    
    return {
        "collection": [
            {**f, "caught": f["id"] in caught}
            for f in FISH
        ]
    }

if os.path.exists("games/FishingGame/index.html"):
    app.mount("/FishingGame", StaticFiles(directory="games/FishingGame", html=True), name="fishing")

app.mount("/style", StaticFiles(directory="pages/styles"), name="style")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)