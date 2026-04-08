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
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import uvicorn
from fish_logic import pick_fish
from fish_data import FISH_BY_ID, FISH
from ble_manager import BLEManager

app = FastAPI()
app.add_middleware(GZipMiddleware, minimum_size=1000)


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
app.add_middleware(SecurityHeadersMiddleware)


@app.get("/")
async def serve_frontend():
    return FileResponse("index.html")

@app.get("/Start")
def landing():
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

    # Check before adding so we can report if it's truly new
    already_caught = patient_id in caught_collection and fish["id"] in caught_collection[patient_id]

    if patient_id not in caught_collection:
        caught_collection[patient_id] = set()
    caught_collection[patient_id].add(fish["id"])

    return {
        "fish": fish,
        "new": not already_caught,
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

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)