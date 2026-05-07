"""
interrogator.py
===============
Connects to a BLE device and interrogates its CSC characteristics
to determine sensor name, mode, location and XOSS compatibility.
"""

import asyncio
from typing import Callable, Optional

from bleak import BleakClient

from .constants import (
    CSC_SERVICE, CSC_MEASUREMENT, CSC_FEATURE,
    SENSOR_LOCATION, DEVICE_NAME, CSC_LOCATIONS,
)
from .models import DeviceInfo


async def connect_and_interrogate(
    address:    str,
    devices:    dict[str, DeviceInfo],
    on_connected:            Callable[[str], None],
    on_disconnected:         Callable[[str], None],
    on_interrogation_result: Callable[[dict], None],
    on_error:                Callable[[str], None],
    on_connect_success:      Callable[[BleakClient], None],
) -> Optional[BleakClient]:
    """
    Connects to the device at address, reads CSC characteristics,
    and fires the appropriate result callback.
    Returns the connected BleakClient on success, None on failure.
    """
    print(f"[BLE] Connecting to {address} …")
    client: Optional[BleakClient] = None

    def _on_disconnect(_=None):
        on_disconnected(address)
        print(f"[BLE] Disconnected from {address}")

    try:
        client = BleakClient(address, timeout=10.0, disconnected_callback=_on_disconnect)
        await client.connect()
        print(f"[BLE] Connected. Interrogating …")

        all_uuids = []
        for svc in client.services:
            all_uuids.append(str(svc.uuid).lower())
            for char in svc.characteristics:
                all_uuids.append(str(char.uuid).lower())

        if address in devices:
            devices[address].services = [str(s.uuid) for s in client.services]

        has_csc = (
            CSC_SERVICE.lower()     in all_uuids or
            CSC_MEASUREMENT.lower() in all_uuids
        )

        if not has_csc:
            print(f"[BLE] No CSC — rejecting.")
            await client.disconnect()
            on_interrogation_result({
                "accepted": False,
                "address":  address,
                "name":     devices.get(address, DeviceInfo(address,"",0,"",False)).name,
                "reason":   "No cycling sensor data found on this device.",
            })
            return None

        name = ""; mode = "unknown"; location = "Unknown"; features = []

        try:
            name = (await client.read_gatt_char(DEVICE_NAME)).decode("utf-8", errors="replace")
        except Exception: pass

        try:
            loc_byte = (await client.read_gatt_char(SENSOR_LOCATION))[0]
            location = CSC_LOCATIONS.get(loc_byte, f"0x{loc_byte:02X}")
        except Exception: pass

        try:
            flags = int.from_bytes(await client.read_gatt_char(CSC_FEATURE), "little")
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
                await client.start_notify(CSC_MEASUREMENT, on_csc)
                try: await asyncio.wait_for(got.wait(), timeout=3.0)
                except asyncio.TimeoutError: pass
                await client.stop_notify(CSC_MEASUREMENT)
                if csc_data:
                    f = csc_data[0][0]
                    if f & 0x01:   mode = "speed"
                    elif f & 0x02: mode = "cadence"
            except Exception: pass

        is_xoss = "XOSS" in name.upper() or "ARENA" in name.upper()
        on_connected(address)
        on_connect_success(client)
        on_interrogation_result({
            "accepted": True,
            "address":  address,
            "name":     name,
            "mode":     mode,
            "location": location,
            "is_xoss":  is_xoss,
            "features": features,
        })
        print(f"[BLE] Accepted: {name} | mode={mode} | xoss={is_xoss}")
        return client

    except Exception as e:
        msg = f"Connect failed: {e}"
        print(f"[BLE] {msg}")
        on_error(msg)
        return None
