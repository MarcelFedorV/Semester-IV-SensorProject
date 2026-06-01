"""
test_sensor_js.py
=================
Tests for the browser-side sensor logic (sensor_connect.js / sensor_frame.js).
Since this is Python, we replicate the JS CSCMetrics calculations and
command-building logic here to verify correctness independently.
"""

import unittest
import struct


# ── CSC packet helpers (mirrors the JS DataView parsing) ─────────────────────

def build_csc_packet(wheel_revs=None, wheel_time=None, crank_revs=None, crank_time=None):
    """Build a raw CSC measurement packet the same way the sensor would."""
    flags = 0
    data = bytearray()

    if wheel_revs is not None:
        flags |= 0x01
    if crank_revs is not None:
        flags |= 0x02

    data.append(flags)

    if wheel_revs is not None:
        data += struct.pack('<IH', wheel_revs, wheel_time)
    if crank_revs is not None:
        data += struct.pack('<HH', crank_revs, crank_time)

    return bytes(data)


def parse_csc_flags(packet):
    """Returns (has_wheel, has_crank) from the flags byte."""
    flags = packet[0]
    return bool(flags & 0x01), bool(flags & 0x02)


# ── XOSS command helpers (mirrors makeCmd in JS) ──────────────────────────────

def make_cmd(value):
    """[0x30, value, 0x30 XOR value] — mirrors JS makeCmd()."""
    return bytes([0x30, value, 0x30 ^ value])


def is_valid_cmd(cmd):
    """Verify the checksum byte is correct."""
    return len(cmd) == 3 and cmd[0] == 0x30 and cmd[2] == (0x30 ^ cmd[1])


def compute_cadence_jump(current_counter):
    """Delta needed to reach 0x24 — mirrors the cadence switch logic."""
    return (0x24 - current_counter) & 0xFF


# ── CSC metric calculations (mirrors CSCMetrics class in JS) ──────────────────

WHEEL_CIRCUMFERENCE = 2.1   # metres
GEAR_RATIO          = 2.8
TIME_RESOLUTION     = 1024  # ticks per second


def calc_speed(delta_revs, delta_ticks):
    """Returns speed in m/s given wheel revolution delta and time delta in ticks."""
    if delta_ticks == 0:
        return 0.0
    seconds = delta_ticks / TIME_RESOLUTION
    distance = delta_revs * WHEEL_CIRCUMFERENCE
    return distance / seconds


def calc_cadence(delta_revs, delta_ticks):
    """Returns cadence in RPM given crank revolution delta and time delta in ticks."""
    if delta_ticks == 0:
        return 0.0
    seconds = delta_ticks / TIME_RESOLUTION
    return (delta_revs / seconds) * 60


# ═════════════════════════════════════════════════════════════════════════════

class TestCSCPacketParsing(unittest.TestCase):

    def test_speed_only_flags(self):
        packet = build_csc_packet(wheel_revs=100, wheel_time=1024)
        has_wheel, has_crank = parse_csc_flags(packet)
        self.assertTrue(has_wheel)
        self.assertFalse(has_crank)

    def test_cadence_only_flags(self):
        packet = build_csc_packet(crank_revs=50, crank_time=512)
        has_wheel, has_crank = parse_csc_flags(packet)
        self.assertFalse(has_wheel)
        self.assertTrue(has_crank)

    def test_combined_flags(self):
        packet = build_csc_packet(wheel_revs=100, wheel_time=1024, crank_revs=50, crank_time=512)
        has_wheel, has_crank = parse_csc_flags(packet)
        self.assertTrue(has_wheel)
        self.assertTrue(has_crank)

    def test_wheel_data_roundtrip(self):
        packet = build_csc_packet(wheel_revs=1234, wheel_time=2048)
        # skip flags byte, read wheel_revs (4 bytes) and wheel_time (2 bytes)
        wheel_revs = struct.unpack_from('<I', packet, 1)[0]
        wheel_time = struct.unpack_from('<H', packet, 5)[0]
        self.assertEqual(wheel_revs, 1234)
        self.assertEqual(wheel_time, 2048)

    def test_crank_data_roundtrip(self):
        packet = build_csc_packet(crank_revs=77, crank_time=300)
        crank_revs = struct.unpack_from('<H', packet, 1)[0]
        crank_time = struct.unpack_from('<H', packet, 3)[0]
        self.assertEqual(crank_revs, 77)
        self.assertEqual(crank_time, 300)


class TestCSCMetrics(unittest.TestCase):

    def test_speed_calculation(self):
        # 1 revolution in 1 second (1024 ticks), 2.1m circumference = 2.1 m/s
        speed = calc_speed(delta_revs=1, delta_ticks=1024)
        self.assertAlmostEqual(speed, 2.1, places=5)

    def test_speed_zero_when_no_time_elapsed(self):
        speed = calc_speed(delta_revs=5, delta_ticks=0)
        self.assertEqual(speed, 0.0)

    def test_cadence_calculation(self):
        # 1 crank revolution in 1 second = 60 RPM
        cadence = calc_cadence(delta_revs=1, delta_ticks=1024)
        self.assertAlmostEqual(cadence, 60.0, places=5)

    def test_cadence_zero_when_no_time_elapsed(self):
        cadence = calc_cadence(delta_revs=3, delta_ticks=0)
        self.assertEqual(cadence, 0.0)

    def test_speed_kmh_conversion(self):
        speed_ms = calc_speed(delta_revs=1, delta_ticks=1024)  # 2.1 m/s
        speed_kmh = speed_ms * 3.6
        self.assertAlmostEqual(speed_kmh, 7.56, places=4)

    def test_distance_accumulation(self):
        # 10 wheel revolutions = 21 metres
        distance = 10 * WHEEL_CIRCUMFERENCE
        self.assertAlmostEqual(distance, 21.0, places=5)


class TestXOSSCommands(unittest.TestCase):

    def test_make_cmd_checksum(self):
        # Third byte must always be 0x30 XOR value
        for val in [0x00, 0x01, 0x24, 0xFF, 0x10]:
            cmd = make_cmd(val)
            self.assertTrue(is_valid_cmd(cmd), f"Checksum failed for value 0x{val:02X}")

    def test_make_cmd_header(self):
        cmd = make_cmd(0x42)
        self.assertEqual(cmd[0], 0x30)

    def test_make_cmd_length(self):
        cmd = make_cmd(0x01)
        self.assertEqual(len(cmd), 3)

    def test_ping_command(self):
        # The ping to read the counter is makeCmd(0x01) = [0x30, 0x01, 0x31]
        cmd = make_cmd(0x01)
        self.assertEqual(cmd, bytes([0x30, 0x01, 0x31]))

    def test_cadence_jump_from_zero(self):
        # Counter at 0x00 → jump should be 0x24
        jump = compute_cadence_jump(0x00)
        self.assertEqual(jump, 0x24)

    def test_cadence_jump_from_nonzero(self):
        # Counter at 0x10 → jump should be 0x14
        jump = compute_cadence_jump(0x10)
        self.assertEqual(jump, 0x14)

    def test_cadence_jump_wraps(self):
        # Counter already past 0x24 → jump wraps around via & 0xFF
        jump = compute_cadence_jump(0x30)
        self.assertEqual(jump, (0x24 - 0x30) & 0xFF)
        self.assertGreater(jump, 0)

    def test_cadence_target_command(self):
        # The final command sent should always make the counter reach 0x24
        for counter in [0x00, 0x01, 0x10, 0x20, 0x23]:
            jump = compute_cadence_jump(counter)
            cmd = make_cmd(jump)
            self.assertTrue(is_valid_cmd(cmd))

    def test_sweep_covers_all_bytes(self):
        # The speed switch sweeps 0x00 to 0xFF — verify full coverage
        sweep = [make_cmd(v) for v in range(0x100)]
        self.assertEqual(len(sweep), 256)
        self.assertTrue(all(is_valid_cmd(c) for c in sweep))


class TestSensorModeDetection(unittest.TestCase):

    def test_detects_speed_mode(self):
        packet = build_csc_packet(wheel_revs=1, wheel_time=100)
        has_wheel, has_crank = parse_csc_flags(packet)
        mode = 'speed' if has_wheel and not has_crank else None
        self.assertEqual(mode, 'speed')

    def test_detects_cadence_mode(self):
        packet = build_csc_packet(crank_revs=1, crank_time=100)
        has_wheel, has_crank = parse_csc_flags(packet)
        mode = 'cadence' if has_crank and not has_wheel else None
        self.assertEqual(mode, 'cadence')

    def test_detects_combined_mode(self):
        packet = build_csc_packet(wheel_revs=1, wheel_time=100, crank_revs=1, crank_time=100)
        has_wheel, has_crank = parse_csc_flags(packet)
        mode = 'combined' if has_wheel and has_crank else None
        self.assertEqual(mode, 'combined')


if __name__ == "__main__":
    unittest.main(verbosity=2)
