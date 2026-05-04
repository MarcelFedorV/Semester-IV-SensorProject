"""
xoss.py
=======
XOSS sensor mode-switching helpers (cadence ↔ speed).
"""

import asyncio
from bleak import BleakClient
from .constants import NUS_UNK, SC_CP


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