# Minimal models for sensor device tests
class DeviceInfo:
    def __init__(self, address, name, rssi, last_seen=None, connectable=False):
        self.address = address
        self.name = name
        self.rssi = rssi
        self.last_seen = last_seen
        self.connectable = connectable

    @property
    def display_name(self):
        return self.name if self.name else self.address

    def info(self):
        return {
            'address': self.address,
            'name': self.display_name,
            'rssi': self.rssi,
        }
