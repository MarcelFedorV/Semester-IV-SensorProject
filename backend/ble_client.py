"""
ble_client.py
=============
Drop-in replacement for direct BLEManager usage inside your Docker container.

Instead of driving Bluetooth directly, this module connects to the
ble_bridge.py process running on the host and re-exposes the exact same
callback interface that BLEManager had — so the rest of your backend code
needs zero changes.

Configuration (environment variables)
--------------------------------------
    BLE_BRIDGE_URL   WebSocket URL of the bridge
                     Default: ws://host.docker.internal:8765
                     Linux Docker: ws://172.17.0.1:8765

Usage (identical to BLEManager)
---------------------------------
    from ble_client import BLEClient

    ble = BLEClient()
    ble.on_device_updated       = lambda d: ...
    ble.on_interrogation_result = lambda r: ...

    await ble.connect_to_bridge()   # call once at startup
    await ble.start_scan(duration=8)
    await ble.connect(address)
    await ble.disconnect()
    await ble.do_mode_switch(address, current_mode)
    await ble.close()               # clean shutdown
"""

import asyncio
import json
import logging
import os
from typing import Callable, Optional

import websockets
from websockets.client import WebSocketClientProtocol

log = logging.getLogger(__name__)

_DEFAULT_URL = os.getenv("BLE_BRIDGE_URL", "ws://host.docker.internal:8765")


class BLEClient:
    """
    Mirrors the BLEManager public API (callbacks + async methods).
    All BLE work is done by ble_bridge.py on the host; this class
    just serialises commands and deserialises events.
    """

    def __init__(self, bridge_url: str = _DEFAULT_URL):
        self.bridge_url = bridge_url
        self._ws: Optional[WebSocketClientProtocol] = None
        self._listener_task: Optional[asyncio.Task] = None
        self._pending_acks: dict[str, asyncio.Future] = {}

        # ── Callbacks (same names as BLEManager) ─────────────────────────────
        self.on_device_updated:       Callable[[dict], None] = lambda d: None
        self.on_device_removed:       Callable[[str],  None] = lambda a: None
        self.on_scan_started:         Callable[[], None]     = lambda: None
        self.on_scan_stopped:         Callable[[], None]     = lambda: None
        self.on_connected:            Callable[[str], None]  = lambda a: None
        self.on_disconnected:         Callable[[str], None]  = lambda a: None
        self.on_error:                Callable[[str], None]  = lambda m: None
        self.on_interrogation_result: Callable[[dict], None] = lambda r: None
        self.on_switch_progress:      Callable[[str],  None] = lambda m: None
        self.on_switch_done:          Callable[[dict], None] = lambda r: None
        # Extra callbacks only the client needs
        self.on_devices_list:         Callable[[list], None] = lambda l: None
        self.on_status:               Callable[[dict], None] = lambda s: None
        self.on_bridge_connected:     Callable[[], None]     = lambda: None
        self.on_bridge_disconnected:  Callable[[], None]     = lambda: None

    # ── Connection lifecycle ──────────────────────────────────────────────────

    async def connect_to_bridge(self, retry_interval: float = 5.0):
        """
        Connect to the bridge and start the background listener.
        Retries indefinitely until successful — useful at container startup
        when the bridge might not be up yet.
        """
        while True:
            try:
                self._ws = await websockets.connect(self.bridge_url)
                log.info("Connected to BLE bridge at %s", self.bridge_url)
                self._listener_task = asyncio.create_task(self._listen())
                self.on_bridge_connected()
                return
            except Exception as e:
                log.warning("Bridge not reachable (%s) — retrying in %ss", e, retry_interval)
                await asyncio.sleep(retry_interval)

    async def close(self):
        """Gracefully close the WebSocket connection."""
        if self._listener_task:
            self._listener_task.cancel()
        if self._ws:
            await self._ws.close()
        self._ws = None
        log.info("BLE client closed.")

    @property
    def is_bridge_connected(self) -> bool:
        if self._ws is None:
            return False
        # websockets >= 14 uses close_code, older versions use closed
        try:
            return not self._ws.closed
        except AttributeError:
            return self._ws.close_code is None

    # ── Listener ──────────────────────────────────────────────────────────────

    async def _listen(self):
        """Background task: read events from the bridge and fire callbacks."""
        try:
            async for raw in self._ws:
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    log.warning("Non-JSON from bridge: %s", raw)
                    continue
                self._dispatch(msg)
        except websockets.exceptions.ConnectionClosedOK:
            pass
        except Exception as e:
            log.error("Bridge listener error: %s", e)
        finally:
            self._ws = None
            self.on_bridge_disconnected()
            log.info("Bridge connection lost.")

    def _dispatch(self, msg: dict):
        event = msg.get("event", "")
        log.debug("→ event: %s", event)

        if event == "scan_started":
            self.on_scan_started()
        elif event == "scan_stopped":
            self.on_scan_stopped()
        elif event == "device_updated":
            self.on_device_updated(msg["device"])
        elif event == "device_removed":
            self.on_device_removed(msg["address"])
        elif event == "connected":
            self.on_connected(msg["address"])
        elif event == "disconnected":
            self.on_disconnected(msg["address"])
        elif event == "error":
            self.on_error(msg["message"])
        elif event == "interrogation_result":
            self.on_interrogation_result(msg["result"])
        elif event == "switch_progress":
            self.on_switch_progress(msg["message"])
        elif event == "switch_done":
            self.on_switch_done(msg["result"])
        elif event == "devices_list":
            self.on_devices_list(msg["devices"])
        elif event == "status":
            self.on_status(msg["status"])
        elif event == "ack":
            cmd = msg.get("cmd", "")
            fut = self._pending_acks.pop(cmd, None)
            if fut and not fut.done():
                fut.set_result(msg)
        else:
            log.debug("Unhandled event: %s", event)

    # ── Command helpers ───────────────────────────────────────────────────────

    async def _send(self, payload: dict) -> dict:
        """Send a command and wait for its ack."""
        if not self.is_bridge_connected:
            raise RuntimeError("Not connected to BLE bridge")
        cmd = payload["cmd"]
        fut: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending_acks[cmd] = fut
        await self._ws.send(json.dumps(payload))
        try:
            return await asyncio.wait_for(fut, timeout=10.0)
        except asyncio.TimeoutError:
            self._pending_acks.pop(cmd, None)
            raise TimeoutError(f"No ack received for command '{cmd}'")

    # ── Public API (mirrors BLEManager) ──────────────────────────────────────

    async def start_scan(self, duration: float = 8.0) -> dict:
        return await self._send({"cmd": "scan_once", "duration": duration})

    async def start_scan_continuous(self) -> dict:
        return await self._send({"cmd": "scan_start"})

    async def stop_scan(self) -> dict:
        return await self._send({"cmd": "scan_stop"})

    async def clear_devices(self) -> dict:
        """Clear the bridge's device cache."""
        return await self._send({"cmd": "clear_devices"})

    async def get_devices(self):
        """
        Request the current device list.
        Result arrives via on_devices_list callback.
        """
        await self._ws.send(json.dumps({"cmd": "get_devices"}))

    async def get_status(self):
        """
        Request the current bridge status.
        Result arrives via on_status callback.
        """
        await self._ws.send(json.dumps({"cmd": "get_status"}))

    async def connect_and_interrogate(self, address: str) -> dict:
        return await self._send({"cmd": "connect", "address": address})

    async def disconnect(self) -> dict:
        """Disconnect the currently connected BLE device."""
        return await self._send({"cmd": "disconnect"})

    async def do_mode_switch(self, address: str, current_mode: str) -> dict:
        return await self._send({
            "cmd":          "mode_switch",
            "address":      address,
            "current_mode": current_mode,
        })