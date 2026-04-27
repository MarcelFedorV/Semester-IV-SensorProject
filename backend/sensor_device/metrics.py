"""
metrics.py
==========
Calculates speed, cadence and distance from raw CSC measurement bytes.

Assumptions (adjustable):
  WHEEL_CIRCUMFERENCE — average 700c × 25mm road tyre ≈ 2.1 m
  GEAR_RATIO          — crank rev → wheel revs, typical mid-gear ≈ 2.8

If the sensor reports wheel revolution data directly (speed mode), the gear
ratio is not used. If it only reports crank revolutions (cadence mode), speed
and distance are derived via: speed = cadence × gear_ratio × circumference.

CSC event timestamps are in 1/1024 second units and roll over at 65535.
Cumulative wheel revolutions roll over at 2^32, crank at 2^16.
"""

WHEEL_CIRCUMFERENCE: float = 2.1   # metres
GEAR_RATIO:          float = 2.8   # wheel revs per crank rev
TIME_RESOLUTION:     int   = 1024  # ticks per second


class CSCMetrics:
    """
    Stateful parser for CSC measurement notifications.
    Call update(data) on every notification; it returns a fresh metrics dict.
    """

    def __init__(
        self,
        wheel_circumference: float = WHEEL_CIRCUMFERENCE,
        gear_ratio:          float = GEAR_RATIO,
    ):
        self.wheel_circumference = wheel_circumference
        self.gear_ratio          = gear_ratio

        self._last_wheel_revs: int | None = None
        self._last_wheel_time: int | None = None
        self._last_crank_revs: int | None = None
        self._last_crank_time: int | None = None

        self.distance_m:   float = 0.0
        self.speed_ms:     float = 0.0
        self.cadence_rpm:  float = 0.0

    # ── Public ────────────────────────────────────────────────────────────────

    def update(self, data: bytes) -> dict:
        """Parse one CSC notification and return updated metrics."""
        if len(data) < 1:
            return self._snapshot()

        flags  = data[0]
        offset = 1
        has_wheel = bool(flags & 0x01)
        has_crank = bool(flags & 0x02)

        if has_wheel and len(data) >= offset + 6:
            offset = self._parse_wheel(data, offset)

        if has_crank and len(data) >= offset + 4:
            self._parse_crank(data, offset, derive_speed=not has_wheel)

        return self._snapshot()

    def reset(self):
        """Zero out all accumulated state (e.g. on reconnect)."""
        self._last_wheel_revs = None
        self._last_wheel_time = None
        self._last_crank_revs = None
        self._last_crank_time = None
        self.distance_m  = 0.0
        self.speed_ms    = 0.0
        self.cadence_rpm = 0.0

    # ── Internal ──────────────────────────────────────────────────────────────

    def _parse_wheel(self, data: bytes, offset: int) -> int:
        wheel_revs = int.from_bytes(data[offset:offset + 4], "little")
        wheel_time = int.from_bytes(data[offset + 4:offset + 6], "little")

        if self._last_wheel_revs is not None:
            delta_revs = (wheel_revs - self._last_wheel_revs) & 0xFFFF_FFFF
            delta_time = (wheel_time - self._last_wheel_time) & 0xFFFF
            if delta_time > 0:
                elapsed_s = delta_time / TIME_RESOLUTION
                dist = delta_revs * self.wheel_circumference
                self.distance_m += dist
                self.speed_ms    = dist / elapsed_s

        self._last_wheel_revs = wheel_revs
        self._last_wheel_time = wheel_time
        return offset + 6

    def _parse_crank(self, data: bytes, offset: int, derive_speed: bool):
        crank_revs = int.from_bytes(data[offset:offset + 2], "little")
        crank_time = int.from_bytes(data[offset + 2:offset + 4], "little")

        if self._last_crank_revs is not None:
            delta_revs = (crank_revs - self._last_crank_revs) & 0xFFFF
            delta_time = (crank_time - self._last_crank_time) & 0xFFFF
            if delta_time > 0:
                elapsed_s        = delta_time / TIME_RESOLUTION
                self.cadence_rpm = (delta_revs / elapsed_s) * 60.0

                if derive_speed:
                    # Estimate wheel speed from cadence + assumed gear ratio
                    wheel_rps     = (self.cadence_rpm / 60.0) * self.gear_ratio
                    self.speed_ms = wheel_rps * self.wheel_circumference
                    self.distance_m += self.speed_ms * elapsed_s

        self._last_crank_revs = crank_revs
        self._last_crank_time = crank_time

    def _snapshot(self) -> dict:
        return {
            "speed_ms":    round(self.speed_ms, 3),
            "speed_kmh":   round(self.speed_ms * 3.6, 2),
            "cadence_rpm": round(self.cadence_rpm, 1),
            "distance_m":  round(self.distance_m, 1),
            "distance_km": round(self.distance_m / 1000, 3),
        }