"""
main.py — FastAPI server bridging BLE manager to browser.

pip install fastapi uvicorn bleak
python main.py  →  http://localhost:8000
"""

import asyncio
import json
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
import uvicorn

from ble_manager import BLEManager

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

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def serve_frontend():
    return FileResponse("index.html")

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
    try:
        while True:
            raw = await ws.receive_text()
            await handle_message(ws, json.loads(raw))
    except WebSocketDisconnect:
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


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)