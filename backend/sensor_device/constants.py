"""
constants.py
============
BLE UUIDs and lookup tables for CSC sensors.
"""

CSC_SERVICE     = "00001816-0000-1000-8000-00805f9b34fb"
CSC_MEASUREMENT = "00002a5b-0000-1000-8000-00805f9b34fb"
CSC_FEATURE     = "00002a5c-0000-1000-8000-00805f9b34fb"
SENSOR_LOCATION = "00002a5d-0000-1000-8000-00805f9b34fb"
DEVICE_NAME     = "00002a00-0000-1000-8000-00805f9b34fb"
NUS_UNK         = "6e400004-b5a3-f393-e0a9-e50e24dcca9e"
SC_CP           = "00002a55-0000-1000-8000-00805f9b34fb"

CSC_LOCATIONS = {
    0:  "Other",        1:  "Top of Shoe",  2:  "In Shoe",
    3:  "Hip",          4:  "Front Wheel",  5:  "Left Crank",
    6:  "Right Crank",  7:  "Left Pedal",   8:  "Right Pedal",
    9:  "Front Hub",    10: "Rear Dropout", 11: "Chainstay",
    12: "Rear Wheel",   13: "Rear Hub",     14: "Chest",
    15: "Spider",       16: "Chain Ring",
}
