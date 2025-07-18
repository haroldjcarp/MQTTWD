"""
Device Manager for C-Bus Lights integration.
Simplified version that works within Home Assistant custom component structure.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class DeviceType(Enum):
    """C-Bus device types."""
    LIGHT = "light"
    FAN = "fan"
    SWITCH = "switch"
    SENSOR = "sensor"
    BINARY_SENSOR = "binary_sensor"
    COVER = "cover"
    CLIMATE = "climate"


@dataclass
class Device:
    """Represents a C-Bus device."""
    group: int
    name: str
    device_type: DeviceType
    area: Optional[str] = None
    icon: Optional[str] = None
    dimmable: bool = False
    fade_time: int = 0
    unit_of_measurement: Optional[str] = None
    device_class: Optional[str] = None
    state_class: Optional[str] = None
    unique_id: Optional[str] = None
    manufacturer: str = "Clipsal"
    model: str = "C-Bus Device"
    template: Optional[str] = None
    custom_attributes: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Post-initialization processing."""
        if self.unique_id is None:
            self.unique_id = f"cbus_{self.group}_{self.device_type.value}"
            
        # Set default icons based on device type
        if self.icon is None:
            self.icon = self._get_default_icon()
            
        # Set device class defaults
        if self.device_class is None:
            self.device_class = self._get_default_device_class()
            
    def _get_default_icon(self) -> str:
        """Get default icon for device type."""
        icon_map = {
            DeviceType.LIGHT: "mdi:lightbulb",
            DeviceType.FAN: "mdi:fan",
            DeviceType.SWITCH: "mdi:light-switch",
            DeviceType.SENSOR: "mdi:thermometer",
            DeviceType.BINARY_SENSOR: "mdi:motion-sensor",
            DeviceType.COVER: "mdi:blinds",
            DeviceType.CLIMATE: "mdi:thermostat"
        }
        return icon_map.get(self.device_type, "mdi:help-circle")
        
    def _get_default_device_class(self) -> Optional[str]:
        """Get default device class."""
        if self.device_type == DeviceType.BINARY_SENSOR:
            return "motion"
        elif self.device_type == DeviceType.SENSOR:
            return "temperature"
        return None


class SimpleDeviceManager:
    """Simplified device manager for Home Assistant integration."""
    
    def __init__(self, config: dict):
        """Initialize device manager."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.devices: Dict[int, Device] = {}
        self.discovered_devices: Dict[int, Device] = {}
        
    def create_sample_devices(self) -> List[Device]:
        """Create sample devices for testing."""
        devices = [
            Device(
                group=1,
                name="Living Room",
                device_type=DeviceType.LIGHT,
                area="Living Room",
                dimmable=True
            ),
            Device(
                group=2,
                name="Kitchen",
                device_type=DeviceType.LIGHT,
                area="Kitchen",
                dimmable=True
            ),
            Device(
                group=3,
                name="Bedroom",
                device_type=DeviceType.LIGHT,
                area="Bedroom",
                dimmable=True
            ),
        ]
        
        for device in devices:
            self.devices[device.group] = device
            
        return devices
        
    def get_devices_by_type(self, device_type: DeviceType) -> List[Device]:
        """Get devices by type."""
        all_devices = list(self.devices.values()) + list(self.discovered_devices.values())
        return [d for d in all_devices if d.device_type == device_type]
        
    def get_device(self, group: int) -> Optional[Device]:
        """Get device by group number."""
        return self.devices.get(group) or self.discovered_devices.get(group)
        
    def get_all_devices(self) -> List[Device]:
        """Get all devices."""
        all_devices = list(self.devices.values()) + list(self.discovered_devices.values())
        return sorted(all_devices, key=lambda d: d.group)
        
    async def query_device_name(self, group: int) -> Optional[str]:
        """Query device name - placeholder for future implementation."""
        device = self.get_device(group)
        return device.name if device else None 