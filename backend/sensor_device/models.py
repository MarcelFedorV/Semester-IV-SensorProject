"""
models.py
=========
Data models for BLE devices.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class DeviceInfo:
    address:      str
    name:         str
    rssi:         int
    last_seen:    str
    connectable:  bool
    services:     list[str]      = field(default_factory=list)
    manufacturer: Optional[str]  = None

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def display_name(self) -> str:
        return self.name if self.name else self.address