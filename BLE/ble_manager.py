"""
ble_manager.py
==============
Generic BLE scanner + CSC interrogation + XOSS mode switch.
"""

import asyncio
import sys
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Callable, Optional
from bleak import BleakScanner, BleakClient
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# ── UUIDs ─────────────────────────────────────────────────────────────────────

CSC_SERVICE     = "00001816-0000-1000-8000-00805f9b34fb"
CSC_MEASUREMENT = "00002a5b-0000-1000-8000-00805f9b34fb"
CSC_FEATURE     = "00002a5c-0000-1000-8000-00805f9b34fb"
SENSOR_LOCATION = "00002a5d-0000-1000-8000-00805f9b34fb"
DEVICE_NAME     = "00002a00-0000-1000-8000-00805f9b34fb"
NUS_UNK         = "6e400004-b5a3-f393-e0a9-e50e24dcca9e"
SC_CP           = "00002a55-0000-1000-8000-00805f9b34fb"

CSC_LOCATIONS = {
    0:"Other", 1:"Top of Shoe", 2:"In Shoe", 3:"Hip",
    4:"Front Wheel", 5:"Left Crank", 6:"Right Crank",
    7:"Left Pedal", 8:"Right Pedal", 9:"Front Hub",
    10:"Rear Dropout", 11:"Chainstay", 12:"Rear Wheel",
    13:"Rear Hub", 14:"Chest", 15:"Spider", 16:"Chain Ring",
}

# ── XOSS switch helpers ───────────────────────────────────────────────────────

def make_cmd(v: int) -> bytes:
    return bytes([0x30, v, 0x30 ^ v])

async def _set_location(client: BleakClient, loc: int) -> bool:
    resp = []; got = asyncio.Event()
    def cb(s, d): resp.append(bytes(d)); got.set()
    try:
        await client.start_notify(SC_CP, cb)
        await client.write_gatt_char(SC_CP, bytes([0x03, loc]), response=True)
        try: await asyncio.wait_for(got.wait(), timeout=3.0)
        except asyncio.TimeoutError: pass
        await client.stop_notify(SC_CP)
        return bool(resp) and len(resp[0]) >= 3 and resp[0][2] == 0x01
    except Exception:
        return False

async def xoss_to_cadence(client: BleakClient, rebooted: asyncio.Event, progress_cb=None) -> bool:
    ticks = []
    def on_tick(s, d):
        data = bytes(d)
        if len(data) >= 3 and data[0] == 0x31 and data[2] == (0x31 ^ data[1]):
            ticks.append(data[1])
    try: await client.start_notify(NUS_UNK, on_tick)
    except Exception: pass

    await client.write_gatt_char(NUS_UNK, make_cmd(0x01), response=False)
    await asyncio.sleep(0.5)
    counter = ticks[-1] if ticks else 0x01

    jump = (0x24 - counter) & 0xFF
    if progress_cb: progress_cb(f"Jumping to cadence threshold (+0x{jump:02X})")
    await client.write_gatt_char(NUS_UNK, make_cmd(jump), response=False)

    try: await asyncio.wait_for(rebooted.wait(), timeout=6.0)
    except asyncio.TimeoutError: pass
    return rebooted.is_set()

async def xoss_to_speed(client: BleakClient, rebooted: asyncio.Event, progress_cb=None) -> bool:
    all_ticks = []
    def on_tick(s, d):
        data = bytes(d)
        if len(data) >= 3 and data[0] == 0x31 and data[2] == (0x31 ^ data[1]):
            all_ticks.append(data[1])

    await _set_location(client, 0x04)
    try: await client.start_notify(NUS_UNK, on_tick)
    except Exception: pass

    if progress_cb: progress_cb("Sweeping counter to speed threshold…")

    for val in range(0x100):
        if rebooted.is_set(): break
        try:
            await client.write_gatt_char(NUS_UNK, make_cmd(val), response=False)
        except Exception:
            break
        if val % 32 == 0 and progress_cb:
            progress_cb(f"Sweep 0x{val:02X} / 0xFF")
        await asyncio.sleep(0.08)

    if not rebooted.is_set():
        try: await asyncio.wait_for(rebooted.wait(), timeout=5.0)
        except asyncio.TimeoutError: pass
    return rebooted.is_set()


# ── Device model ──────────────────────────────────────────────────────────────

@dataclass
class DeviceInfo:
    address:      str
    name:         str
    rssi:         int
    last_seen:    str
    connectable:  bool
    services:     list[str] = field(default_factory=list)
    manufacturer: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def display_name(self) -> str:
        return self.name if self.name else f"[{self.address}]"


# ── BLE Manager ───────────────────────────────────────────────────────────────

class BLEManager:

    def __init__(self):
        self.devices:      dict[str, DeviceInfo] = {}
        self._scanning:    bool = False
        self._scanner:     Optional[BleakScanner] = None
        self.client:       Optional[BleakClient] = None
        self.connected_to: Optional[str] = None

        # Hooks
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

    # ── Scanning ──────────────────────────────────────────────────────────────

    def _on_detection(self, device: BLEDevice, adv: AdvertisementData):
        # Only surface devices that advertise the CSC service
        advertised = [str(u).lower() for u in (adv.service_uuids or [])]
        if CSC_SERVICE.lower() not in advertised:
            return

        name = device.name or adv.local_name or ""
        manufacturer = None
        if adv.manufacturer_data:
            cid = next(iter(adv.manufacturer_data))
            manufacturer = f"0x{cid:04X}"
        info = DeviceInfo(
            address      = device.address,
            name         = name,
            rssi         = adv.rssi if adv.rssi is not None else -999,
            last_seen    = datetime.now().isoformat(),
            connectable  = getattr(adv, "connectable", True),
            services     = [str(s) for s in (adv.service_uuids or [])],
            manufacturer = manufacturer,
        )
        is_new = device.address not in self.devices
        self.devices[device.address] = info
        self.on_device_updated(info.to_dict())
        if is_new:
            print(f"  + {info.display_name:<35} {device.address}  RSSI:{info.rssi}")

    async def start_scan(self, duration: float = 8.0):
        if self._scanning: return
        self._scanning = True
        self._scanner  = BleakScanner(detection_callback=self._on_detection)
        self.on_scan_started()
        print(f"[BLE] Scanning ({duration}s) …")
        try:
            await self._scanner.start()
            await asyncio.sleep(duration)
        except Exception as e:
            self.on_error(str(e))
        finally:
            try: await self._scanner.stop()
            except Exception: pass
            self._scanning = False
            self.on_scan_stopped()
            print(f"[BLE] Scan done. {len(self.devices)} device(s) known.")

    async def start_scan_continuous(self):
        if self._scanning: return
        self._scanning = True
        self._scanner  = BleakScanner(detection_callback=self._on_detection)
        self.on_scan_started()
        print("[BLE] Continuous scan started.")
        try:
            await self._scanner.start()
            while self._scanning:
                await asyncio.sleep(0.5)
        except Exception as e:
            self.on_error(str(e))
        finally:
            try: await self._scanner.stop()
            except Exception: pass
            self._scanning = False
            self.on_scan_stopped()

    async def stop_scan(self):
        if not self._scanning: return
        self._scanning = False
        if self._scanner:
            try: await self._scanner.stop()
            except Exception: pass
        print("[BLE] Scan stopped.")

    def get_devices(self) -> list[dict]:
        return [
            d.to_dict()
            for d in sorted(self.devices.values(), key=lambda x: x.rssi, reverse=True)
        ]

    def clear_devices(self):
        addresses = list(self.devices.keys())
        self.devices.clear()
        for a in addresses:
            self.on_device_removed(a)
        print("[BLE] Device list cleared.")

    # ── Connection + interrogation ────────────────────────────────────────────

    async def connect_and_interrogate(self, address: str):
        if self.is_connected:
            await self.disconnect()
        if self._scanning:
            await self.stop_scan()

        print(f"[BLE] Connecting to {address} …")

        def _on_disconnect(_=None):
            self.connected_to = None
            self.client       = None
            self.on_disconnected(address)
            print(f"[BLE] Disconnected from {address}")

        try:
            self.client = BleakClient(
                address, timeout=10.0,
                disconnected_callback=_on_disconnect
            )
            await self.client.connect()
            self.connected_to = address
            print(f"[BLE] Connected. Interrogating …")

            all_uuids = []
            for svc in self.client.services:
                all_uuids.append(str(svc.uuid).lower())
                for char in svc.characteristics:
                    all_uuids.append(str(char.uuid).lower())

            if address in self.devices:
                self.devices[address].services = [str(s.uuid) for s in self.client.services]

            has_csc = (
                CSC_SERVICE.lower()     in all_uuids or
                CSC_MEASUREMENT.lower() in all_uuids
            )

            if not has_csc:
                print(f"[BLE] No CSC — rejecting.")
                await self.client.disconnect()
                self.client = self.connected_to = None
                self.on_interrogation_result({
                    "accepted": False,
                    "address":  address,
                    "name":     self.devices.get(address, DeviceInfo(address,"",0,"",False)).name,
                    "reason":   "No cycling sensor data found on this device.",
                })
                return

            name = ""; mode = "unknown"; location = "Unknown"; features = []

            try:
                name = (await self.client.read_gatt_char(DEVICE_NAME)).decode("utf-8", errors="replace")
            except Exception: pass

            try:
                loc_byte = (await self.client.read_gatt_char(SENSOR_LOCATION))[0]
                location = CSC_LOCATIONS.get(loc_byte, f"0x{loc_byte:02X}")
            except Exception: pass

            try:
                flags = int.from_bytes(await self.client.read_gatt_char(CSC_FEATURE), "little")
                if flags & 0x01: features.append("Wheel Revolution")
                if flags & 0x02: features.append("Crank Revolution")
            except Exception: pass

            if "S1633" in name or "SPD" in name.upper():
                mode = "speed"
            elif "C1633" in name or "CAD" in name.upper():
                mode = "cadence"
            else:
                got = asyncio.Event(); csc_data = []
                def on_csc(s, d):
                    if not csc_data: csc_data.append(bytes(d)); got.set()
                try:
                    await self.client.start_notify(CSC_MEASUREMENT, on_csc)
                    try: await asyncio.wait_for(got.wait(), timeout=3.0)
                    except asyncio.TimeoutError: pass
                    await self.client.stop_notify(CSC_MEASUREMENT)
                    if csc_data:
                        f = csc_data[0][0]
                        if f & 0x01:   mode = "speed"
                        elif f & 0x02: mode = "cadence"
                except Exception: pass

            is_xoss = "XOSS" in name.upper() or "ARENA" in name.upper()
            self.on_connected(address)
            asyncio.create_task(self._monitor_csc(self.client))
            self.on_interrogation_result({
                "accepted": True,
                "address":  address,
                "name":     name,
                "mode":     mode,
                "location": location,
                "is_xoss":  is_xoss,
                "features": features,
            })
            print(f"[BLE] Accepted: {name} | mode={mode} | xoss={is_xoss}")

        except Exception as e:
            msg = f"Connect failed: {e}"
            print(f"[BLE] {msg}")
            self.on_error(msg)
            self.client = self.connected_to = None

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
        if self._scanning:
            await self.stop_scan()

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

        if address in self.devices:
            del self.devices[address]
            self.on_device_removed(address)

        progress("Sensor rebooted — run a new scan to find it in its new mode.")
        self.on_switch_done({
            "success":      True,
            "old_address":  address,
            "target_mode":  target,
        })

    def get_status(self) -> dict:
        return {
            "scanning":     self._scanning,
            "connected":    self.is_connected,
            "connected_to": self.connected_to,
            "device_count": len(self.devices),
        }

    # ── CSC monitor ───────────────────────────────────────────────────────────

    async def _monitor_csc(self, client: BleakClient):
        """
        Subscribes to CSC measurement and reports motion by comparing
        cumulative revolution counters. If the counter hasn't changed
        in STOP_TIMEOUT seconds, the sensor is not moving.
        Works for both wheel (flag bit 0) and crank (flag bit 1) sensors.
        """
        STOP_TIMEOUT = 2.0  # seconds of no counter change = stopped

        last_wheel_revs  = None
        last_crank_revs  = None
        last_change_time = asyncio.get_event_loop().time()

        def on_csc(sender, data):
            nonlocal last_wheel_revs, last_crank_revs, last_change_time
            b     = bytes(data)
            flags = b[0]
            changed = False

            # Wheel revolution data: bytes 1-4 (present if bit 0 set)
            if flags & 0x01 and len(b) >= 5:
                wheel_revs = int.from_bytes(b[1:5], "little")
                if last_wheel_revs is None or wheel_revs != last_wheel_revs:
                    last_wheel_revs  = wheel_revs
                    changed = True

            # Crank revolution data: bytes 5-6 (present if bit 1 set)
            if flags & 0x02 and len(b) >= 7:
                crank_revs = int.from_bytes(b[5:7], "little")
                if last_crank_revs is None or crank_revs != last_crank_revs:
                    last_crank_revs  = crank_revs
                    changed = True

            if changed:
                last_change_time = asyncio.get_event_loop().time()

        try:
            await client.start_notify(CSC_MEASUREMENT, on_csc)
            while client.is_connected:
                await asyncio.sleep(0.5)
                elapsed = asyncio.get_event_loop().time() - last_change_time
                self.on_sensor_state(elapsed < STOP_TIMEOUT)
            await client.stop_notify(CSC_MEASUREMENT)
        except Exception as e:
            print(f"[CSC monitor] stopped: {e}")
        finally:
            self.on_sensor_state(False)