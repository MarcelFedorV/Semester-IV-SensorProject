"""
csc_monitor.py
==============
Monitors CSC measurements, reports motion state and emits live metrics.
"""

import asyncio
from typing import Callable, Optional
from bleak import BleakClient
from .constants import CSC_MEASUREMENT
from .metrics import CSCMetrics


async def monitor_csc(
    client:          BleakClient,
    on_sensor_state: Callable[[bool], None],
    on_metrics:      Optional[Callable[[dict], None]] = None,
) -> None:
    """
    Subscribes to CSC notifications.
    - Calls on_sensor_state(True/False) based on whether the sensor is moving.
    - Calls on_metrics(dict) with speed, cadence and distance on every notification.
    """
    STOP_TIMEOUT = 2.0

    metrics          = CSCMetrics()
    last_wheel_revs  = None
    last_crank_revs  = None
    last_change_time = asyncio.get_event_loop().time()

    def on_csc(sender, data):
        nonlocal last_wheel_revs, last_crank_revs, last_change_time
        b     = bytes(data)
        flags = b[0]
        changed = False

        offset = 1
        if flags & 0x01 and len(b) >= offset + 4:
            wheel_revs = int.from_bytes(b[offset:offset + 4], "little")
            if last_wheel_revs is None or wheel_revs != last_wheel_revs:
                last_wheel_revs = wheel_revs
                changed = True
            offset += 6  # 4 bytes revs + 2 bytes event time

        if flags & 0x02 and len(b) >= offset + 2:
            crank_revs = int.from_bytes(b[offset:offset + 2], "little")
            if last_crank_revs is None or crank_revs != last_crank_revs:
                last_crank_revs = crank_revs
                changed = True

        if changed:
            last_change_time = asyncio.get_event_loop().time()

        if on_metrics:
            on_metrics(metrics.update(b))

    try:
        await client.start_notify(CSC_MEASUREMENT, on_csc)
        while client.is_connected:
            await asyncio.sleep(0.5)
            elapsed = asyncio.get_event_loop().time() - last_change_time
            on_sensor_state(elapsed < STOP_TIMEOUT)
        await client.stop_notify(CSC_MEASUREMENT)
    except Exception as e:
        print(f"[CSC monitor] stopped: {e}")