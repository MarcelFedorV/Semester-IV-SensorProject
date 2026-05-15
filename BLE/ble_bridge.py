"""
ble_bridge.py
=============
Host-side BLE ↔ WebSocket bridge.

Run this DIRECTLY on the host (not in Docker) so it has access to the
system Bluetooth stack.  Your containerised backend connects to it as a
plain WebSocket client.

Usage
-----
    pip install bleak websockets
    python ble_bridge.py [--host 0.0.0.0] [--port 8765]

Protocol
--------
All messages are JSON.  The backend sends COMMANDS; the bridge sends EVENTS.

Commands (backend → bridge)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    {"cmd": "scan_start"}
    {"cmd": "scan_stop"}
    {"cmd": "scan_once",      "duration": 8.0}
    {"cmd": "clear_devices"}
    {"cmd": "get_devices"}
    {"cmd": "get_status"}
    {"cmd": "connect",        "address": "<MAC>"}
    {"cmd": "disconnect"}
    {"cmd": "mode_switch",    "address": "<MAC>", "current_mode": "speed"|"cadence"}

Events (bridge → backend)
~~~~~~~~~~~~~~~~~~~~~~~~~~
    {"event": "scan_started"}
    {"event": "scan_stopped"}
    {"event": "device_updated",        "device": {...}}
    {"event": "device_removed",        "address": "..."}
    {"event": "connected",             "address": "..."}
    {"event": "disconnected",          "address": "..."}
    {"event": "interrogation_result",  "result": {...}}
    {"event": "switch_progress",       "message": "..."}
    {"event": "switch_done",           "result": {...}}
    {"event": "devices_list",          "devices": [...]}
    {"event": "status",                "status": {...}}
    {"event": "error",                 "message": "..."}
    {"event": "ack",                   "cmd": "...", "ok": true}
"""

import asyncio
import json
import argparse
import logging
import sys
from typing import Optional

import websockets
from websockets.server import WebSocketServerProtocol

# ── Import your existing BLE manager ─────────────────────────────────────────
# Adjust the path / package name to match your project layout.
import sys, os
_sd = os.path.join(os.path.dirname(__file__), '..', 'backend', 'sensor_device')
sys.path.insert(0, os.path.dirname(_sd))  # adds backend/ to path
sys.path.insert(0, _sd)
from sensor_device.ble_manager import BLEManager  # import as part of its package


# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [bridge] %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ble_bridge")

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


# ─────────────────────────────────────────────────────────────────────────────

class BLEBridge:
    """
    Wraps one BLEManager instance and forwards its events to every connected
    WebSocket client (fan-out).  Multiple clients are supported – useful if
    you have both a backend service and a debug UI connected simultaneously.
    """

    def __init__(self):
        self.ble    = BLEManager()
        self.clients: set[WebSocketServerProtocol] = set()
        self._bg_task: Optional[asyncio.Task] = None
        self._wire_callbacks()

    # ── Callback wiring ───────────────────────────────────────────────────────

    def _wire_callbacks(self):
        m = self.ble

        m.on_scan_started         = lambda:     self._broadcast({"event": "scan_started"})
        m.on_scan_stopped         = lambda:     self._broadcast({"event": "scan_stopped"})
        m.on_device_updated       = lambda d:   self._broadcast({"event": "device_updated",       "device":  d})
        m.on_device_removed       = lambda a:   self._broadcast({"event": "device_removed",        "address": a})
        m.on_connected            = lambda a:   self._broadcast({"event": "connected",             "address": a})
        m.on_disconnected         = lambda a:   self._broadcast({"event": "disconnected",          "address": a})
        m.on_error                = lambda msg: self._broadcast({"event": "error",                 "message": msg})
        m.on_interrogation_result = lambda r:   self._broadcast({"event": "interrogation_result",  "result":  r})
        m.on_switch_progress      = lambda msg: self._broadcast({"event": "switch_progress",       "message": msg})
        m.on_switch_done          = lambda r:   self._broadcast({"event": "switch_done",           "result":  r})

    # ── Fan-out broadcast ─────────────────────────────────────────────────────

    def _broadcast(self, payload: dict):
        """Send a JSON event to every connected WebSocket client."""
        msg = json.dumps(payload)
        dead = set()
        for ws in self.clients:
            try:
                # schedule the coroutine on the running loop without awaiting
                asyncio.get_event_loop().call_soon_threadsafe(
                    lambda w=ws, m=msg: asyncio.ensure_future(self._send(w, m))
                )
            except Exception:
                dead.add(ws)
        self.clients -= dead

    @staticmethod
    async def _send(ws: WebSocketServerProtocol, msg: str):
        try:
            await ws.send(msg)
        except Exception:
            pass  # client disconnected mid-flight

    # ── Command dispatcher ────────────────────────────────────────────────────

    async def _handle_command(self, ws: WebSocketServerProtocol, data: dict):
        cmd = data.get("cmd", "")
        log.info("← cmd: %s", cmd)

        async def ack(ok=True, **extra):
            await ws.send(json.dumps({"event": "ack", "cmd": cmd, "ok": ok, **extra}))

        # ── Scan controls ────────────────────────────────────────────────────
        if cmd == "scan_start":
            if self._bg_task and not self._bg_task.done():
                await ack(ok=False, reason="already scanning")
                return
            self._bg_task = asyncio.create_task(self.ble.start_scan_continuous())
            await ack()

        elif cmd == "scan_once":
            duration = float(data.get("duration", 8.0))
            if self._bg_task and not self._bg_task.done():
                await ack(ok=False, reason="scan already running")
                return
            self._bg_task = asyncio.create_task(self.ble.start_scan(duration))
            await ack()

        elif cmd == "scan_stop":
            await self.ble.stop_scan()
            await ack()

        elif cmd == "clear_devices":
            self.ble.clear_devices()
            await ack()

        # ── Queries ───────────────────────────────────────────────────────────
        elif cmd == "get_devices":
            await ws.send(json.dumps({
                "event":   "devices_list",
                "devices": self.ble.get_devices(),
            }))

        elif cmd == "get_status":
            await ws.send(json.dumps({
                "event":  "status",
                "status": self.ble.get_status(),
            }))

        # ── Connection ────────────────────────────────────────────────────────
        elif cmd == "connect":
            address = data.get("address", "")
            if not address:
                await ack(ok=False, reason="missing 'address'")
                return
            await ack()
            asyncio.create_task(self.ble.connect_and_interrogate(address))

        elif cmd == "disconnect":
            await self.ble.disconnect()
            await ack()

        # ── Mode switch ───────────────────────────────────────────────────────
        elif cmd == "mode_switch":
            address      = data.get("address", "")
            current_mode = data.get("current_mode", "")
            if not address or current_mode not in ("speed", "cadence"):
                await ack(ok=False, reason="missing or invalid 'address'/'current_mode'")
                return
            await ack()
            asyncio.create_task(self.ble.do_mode_switch(address, current_mode))

        else:
            await ack(ok=False, reason=f"unknown command '{cmd}'")

    # ── WebSocket handler (one per client connection) ─────────────────────────

    async def handler(self, ws: WebSocketServerProtocol):
        addr = ws.remote_address
        log.info("Client connected: %s", addr)
        self.clients.add(ws)

        # Immediately push current status so the client can sync
        await ws.send(json.dumps({"event": "status", "status": self.ble.get_status()}))

        try:
            async for raw in ws:
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    await ws.send(json.dumps({"event": "error", "message": "invalid JSON"}))
                    continue
                await self._handle_command(ws, data)

        except websockets.exceptions.ConnectionClosedOK:
            pass
        except websockets.exceptions.ConnectionClosedError as e:
            log.warning("Client %s closed unexpectedly: %s", addr, e)
        finally:
            self.clients.discard(ws)
            log.info("Client disconnected: %s", addr)


# ─────────────────────────────────────────────────────────────────────────────

async def main(host: str, port: int):
    bridge = BLEBridge()
    log.info("BLE bridge listening on ws://%s:%d", host, port)

    async with websockets.serve(bridge.handler, host, port):
        await asyncio.Future()  # run forever


def parse_args():
    p = argparse.ArgumentParser(description="BLE ↔ WebSocket bridge")
    p.add_argument("--host", default="0.0.0.0",
                   help="Interface to listen on (default: 0.0.0.0)")
    p.add_argument("--port", type=int, default=8765,
                   help="Port to listen on (default: 8765)")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        asyncio.run(main(args.host, args.port))
    except KeyboardInterrupt:
        log.info("Stopped.")