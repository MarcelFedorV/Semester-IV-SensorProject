"""
ble_manager.py
==============
Orchestrates scanning, connection, interrogation, CSC monitoring
and XOSS mode switching. All heavy logic lives in the submodules.
"""

import asyncio
import sys
from typing import Callable, Optional

from bleak import BleakClient
from .xoss import xoss_to_cadence, xoss_to_speed
from .scanner import BLEScanner
from .interrogator import connect_and_interrogate
from .csc_monitor import monitor_csc

if sys.platform == "win32":
    asyncio.set_event_loop(asyncio.SelectorEventLoop())


class BLEManager:

    def __init__(self):
        self.client:       Optional[BleakClient] = None
        self.connected_to: Optional[str] = None

        # Hooks — wired by main.py
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
        self.on_sensor_state:         Callable[[bool], None] = lambda active: None
        self.on_metrics:              Callable[[dict], None] = lambda m: None

        self._scanner = BLEScanner(
            on_device_updated = lambda d: self.on_device_updated(d),
            on_device_removed = lambda a: self.on_device_removed(a),
            on_scan_started   = lambda:   self.on_scan_started(),
            on_scan_stopped   = lambda:   self.on_scan_stopped(),
            on_error          = lambda m: self.on_error(m),
        )

    # ── Scanning (delegated to BLEScanner) ───────────────────────────────────

    async def start_scan(self, duration: float = 8.0):
        await self._scanner.start_scan(duration)

    async def start_scan_continuous(self):
        await self._scanner.start_scan_continuous()

    async def stop_scan(self):
        await self._scanner.stop_scan()

    def get_devices(self) -> list[dict]:
        return self._scanner.get_devices()

    def clear_devices(self):
        self._scanner.clear_devices()

    # ── Connection ────────────────────────────────────────────────────────────

    async def connect_and_interrogate(self, address: str):
        if self.is_connected:
            await self.disconnect()
        if self._scanner.is_scanning:
            await self._scanner.stop_scan()

        def _on_connect_success(client: BleakClient):
            self.client       = client
            self.connected_to = address
            asyncio.create_task(monitor_csc(client, self.on_sensor_state, self.on_metrics))

        def _on_disconnected(addr: str):
            self.client       = None
            self.connected_to = None
            self.on_disconnected(addr)

        await connect_and_interrogate(
            address                  = address,
            devices                  = self._scanner.devices,
            on_connected             = self.on_connected,
            on_disconnected          = _on_disconnected,
            on_interrogation_result  = self.on_interrogation_result,
            on_error                 = self.on_error,
            on_connect_success       = _on_connect_success,
        )

    async def disconnect(self):
        if self.client:
            try: await self.client.disconnect()
            except Exception: pass
        self.client = self.connected_to = None

    @property
    def is_connected(self) -> bool:
        return self.client is not None and self.client.is_connected

    # ── XOSS mode switch ──────────────────────────────────────────────────────

    async def do_mode_switch(self, address: str, current_mode: str):
        target = "cadence" if current_mode == "speed" else "speed"
        print(f"[BLE] Mode switch: {current_mode} → {target}")
        self.on_switch_progress(f"Switching to {target}…")

        if self.is_connected:
            await self.disconnect()
        if self._scanner.is_scanning:
            await self._scanner.stop_scan()

        def progress(msg):
            print(f"[SWITCH] {msg}")
            self.on_switch_progress(msg)

        rebooted = asyncio.Event()

        try:
            client = BleakClient(
                address, timeout=10.0,
                disconnected_callback=lambda _=None: rebooted.set()
            )
            await client.connect()

            if target == "cadence":
                await xoss_to_cadence(client, rebooted, progress_cb=progress)
            else:
                await xoss_to_speed(client, rebooted, progress_cb=progress)

            if not rebooted.is_set():
                try: await asyncio.wait_for(rebooted.wait(), timeout=8.0)
                except asyncio.TimeoutError: pass

        except Exception as e:
            print(f"[SWITCH] Error: {e}")
            self.on_switch_done({"success": False, "error": str(e)})
            return

        if not rebooted.is_set():
            self.on_switch_done({"success": False, "error": "Sensor did not reboot"})
            return

        if address in self._scanner.devices:
            del self._scanner.devices[address]
            self.on_device_removed(address)

        progress("Sensor rebooted — run a new scan to find it in its new mode.")
        self.on_switch_done({
            "success":     True,
            "old_address": address,
            "target_mode": target,
        })

    # ── Status ────────────────────────────────────────────────────────────────

    def get_status(self) -> dict:
        return {
            "scanning":     self._scanner.is_scanning,
            "connected":    self.is_connected,
            "connected_to": self.connected_to,
            "device_count": len(self._scanner.devices),
        }