"""
scanner.py
==========
BLE device scanning — detection, start/stop, device list management.
"""

import asyncio
from datetime import datetime
from typing import Callable, Optional

from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from .models import DeviceInfo
from .constants import CSC_SERVICE


class BLEScanner:

    def __init__(
        self,
        on_device_updated: Callable[[dict], None],
        on_device_removed: Callable[[str],  None],
        on_scan_started:   Callable[[], None],
        on_scan_stopped:   Callable[[], None],
        on_error:          Callable[[str], None],
    ):
        self.devices:   dict[str, DeviceInfo] = {}
        self._scanning: bool = False
        self._scanner:  Optional[BleakScanner] = None

        self._on_device_updated = on_device_updated
        self._on_device_removed = on_device_removed
        self._on_scan_started   = on_scan_started
        self._on_scan_stopped   = on_scan_stopped
        self._on_error          = on_error

    def _on_detection(self, device: BLEDevice, adv: AdvertisementData):
        # Only show cycling sensors (CSC service UUID must be advertised)
        service_uuids = [str(s).lower() for s in (adv.service_uuids or [])]
        if CSC_SERVICE.lower() not in service_uuids:
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
        self._on_device_updated(info.to_dict())
        if is_new:
            print(f"  + {info.display_name:<35} {device.address}  RSSI:{info.rssi}")

    async def start_scan(self, duration: float = 8.0):
        if self._scanning: return
        self._scanning = True
        self._scanner  = BleakScanner(detection_callback=self._on_detection)
        self._on_scan_started()
        print(f"[BLE] Scanning ({duration}s) …")
        try:
            await self._scanner.start()
            await asyncio.sleep(duration)
        except Exception as e:
            self._on_error(str(e))
        finally:
            try: await self._scanner.stop()
            except Exception: pass
            self._scanning = False
            self._on_scan_stopped()
            print(f"[BLE] Scan done. {len(self.devices)} device(s) known.")

    async def start_scan_continuous(self):
        if self._scanning: return
        self._scanning = True
        self._scanner  = BleakScanner(detection_callback=self._on_detection)
        self._on_scan_started()
        print("[BLE] Continuous scan started.")
        try:
            await self._scanner.start()
            while self._scanning:
                await asyncio.sleep(0.5)
        except Exception as e:
            self._on_error(str(e))
        finally:
            try: await self._scanner.stop()
            except Exception: pass
            self._scanning = False
            self._on_scan_stopped()

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
            self._on_device_removed(a)
        print("[BLE] Device list cleared.")

    @property
    def is_scanning(self) -> bool:
        return self._scanning
