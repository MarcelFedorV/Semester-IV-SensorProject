"""
Minimal constants for sensor device tests.

Notes:
- `CSC_LOCATIONS` maps numeric CSC (Cycling Speed and Cadence) location codes
    to human-readable labels. Multiple codes can map to the same label (for
    example codes `2` and `12` both correspond to the rear wheel on some
    sensors). The keys are the canonical numeric codes and must remain unique;
    duplicate values are intentional and represent distinct codes for the same
    physical location.
"""

CSC_SERVICE = "00001816-0000-1000-8000-00805f9b34fb"
CSC_MEASUREMENT = "00002a5b-0000-1000-8000-00805f9b34fb"

# Example location mapping used by tests
CSC_LOCATIONS = {
        0: "Other",
        1: "Front Wheel",
        2: "Rear Wheel",
        12: "Rear Wheel",  # distinct code that maps to same label
}
