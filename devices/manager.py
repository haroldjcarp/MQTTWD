"""
Device Manager for C-Bus MQTT Bridge
Handles device configuration, discovery, and mapping
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from config.config import Config


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
        
    def to_ha_config(self) -> Dict[str, Any]:
        """Convert to Home Assistant configuration format."""
        config = {
            "name": self.name,
            "unique_id": self.unique_id,
            "device": {
                "identifiers": [f"cbus_{self.group}"],
                "name": self.name,
                "manufacturer": self.manufacturer,
                "model": self.model,
                "via_device": "cbus_bridge"
            }
        }
        
        # Add area if specified
        if self.area:
            config["device"]["suggested_area"] = self.area
            
        # Add icon
        if self.icon:
            config["icon"] = self.icon
            
        # Add device class
        if self.device_class:
            config["device_class"] = self.device_class
            
        # Add state class for sensors
        if self.state_class and self.device_type == DeviceType.SENSOR:
            config["state_class"] = self.state_class
            
        # Add unit of measurement
        if self.unit_of_measurement:
            config["unit_of_measurement"] = self.unit_of_measurement
            
        # Device type specific configuration
        if self.device_type == DeviceType.LIGHT:
            config["brightness"] = self.dimmable
            if self.dimmable:
                config["brightness_scale"] = 255
                
        elif self.device_type == DeviceType.FAN:
            config["speed"] = self.dimmable
            if self.dimmable:
                config["speed_range"] = [1, 255]
                
        # Add custom attributes
        config.update(self.custom_attributes)
        
        return config


@dataclass
class DeviceTemplate:
    """Device template for common configurations."""
    name: str
    device_type: DeviceType
    dimmable: bool = False
    fade_time: int = 0
    icon: Optional[str] = None
    device_class: Optional[str] = None
    state_class: Optional[str] = None
    unit_of_measurement: Optional[str] = None
    custom_attributes: Dict[str, Any] = field(default_factory=dict)


class DeviceManager:
    """Manages C-Bus devices and their configurations."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Device storage
        self.devices: Dict[int, Device] = {}
        self.templates: Dict[str, DeviceTemplate] = {}
        
        # Discovery tracking
        self.discovered_devices: Dict[int, Device] = {}
        self.auto_discovery_enabled = config.get('discovery.auto_discovery', True)
        
    async def initialize(self):
        """Initialize device manager."""
        self.logger.info("Initializing device manager")
        
        # Load device templates
        await self._load_templates()
        
        # Load configured devices
        await self._load_devices()
        
        # Setup auto-discovery if enabled
        if self.auto_discovery_enabled:
            await self._setup_auto_discovery()
            
        self.logger.info(f"Initialized {len(self.devices)} devices with {len(self.templates)} templates")
        
    async def _load_templates(self):
        """Load device templates from configuration."""
        template_configs = self.config.get_templates()
        
        for template_config in template_configs:
            try:
                template = DeviceTemplate(
                    name=template_config['name'],
                    device_type=DeviceType(template_config['type']),
                    dimmable=template_config.get('dimmable', False),
                    fade_time=template_config.get('fade_time', 0),
                    icon=template_config.get('icon'),
                    device_class=template_config.get('device_class'),
                    state_class=template_config.get('state_class'),
                    unit_of_measurement=template_config.get('unit_of_measurement'),
                    custom_attributes=template_config.get('custom_attributes', {})
                )
                
                self.templates[template.name] = template
                self.logger.debug(f"Loaded template: {template.name}")
                
            except Exception as e:
                self.logger.error(f"Error loading template {template_config.get('name', 'unknown')}: {e}")
                
    async def _load_devices(self):
        """Load device configurations."""
        device_configs = self.config.get_devices()
        
        for device_config in device_configs:
            try:
                device = await self._create_device_from_config(device_config)
                self.devices[device.group] = device
                self.logger.debug(f"Loaded device: {device.name} (group {device.group})")
                
            except Exception as e:
                self.logger.error(f"Error loading device {device_config.get('name', 'unknown')}: {e}")
                
    async def _create_device_from_config(self, config: Dict[str, Any]) -> Device:
        """Create device from configuration."""
        # Apply template if specified
        template_name = config.get('template')
        if template_name and template_name in self.templates:
            template = self.templates[template_name]
            
            # Merge template defaults with config
            device_config = {
                'device_type': template.device_type.value,
                'dimmable': template.dimmable,
                'fade_time': template.fade_time,
                'icon': template.icon,
                'device_class': template.device_class,
                'state_class': template.state_class,
                'unit_of_measurement': template.unit_of_measurement,
                'custom_attributes': template.custom_attributes.copy()
            }
            
            # Override with specific config
            device_config.update(config)
            config = device_config
            
        # Create device
        device = Device(
            group=config['group'],
            name=config['name'],
            device_type=DeviceType(config['type']),
            area=config.get('area'),
            icon=config.get('icon'),
            dimmable=config.get('dimmable', False),
            fade_time=config.get('fade_time', 0),
            unit_of_measurement=config.get('unit_of_measurement'),
            device_class=config.get('device_class'),
            state_class=config.get('state_class'),
            manufacturer=config.get('manufacturer', 'Clipsal'),
            model=config.get('model', 'C-Bus Device'),
            template=template_name,
            custom_attributes=config.get('custom_attributes', {})
        )
        
        return device
        
    async def _setup_auto_discovery(self):
        """Setup automatic device discovery."""
        self.logger.info("Setting up automatic device discovery")
        
        # TODO: Implement automatic discovery from C-Bus network
        # This would scan the network for devices and create basic configurations
        
    async def discover_device(self, group: int, device_type: DeviceType = DeviceType.LIGHT) -> Optional[Device]:
        """Discover and add a new device."""
        if group in self.devices:
            return self.devices[group]
            
        # Create basic device configuration
        device = Device(
            group=group,
            name=f"C-Bus Device {group}",
            device_type=device_type,
            area="Discovered",
            dimmable=(device_type in [DeviceType.LIGHT, DeviceType.FAN])
        )
        
        self.discovered_devices[group] = device
        self.logger.info(f"Discovered new device: {device.name} (group {group})")
        
        return device
        
    def get_device(self, group: int) -> Optional[Device]:
        """Get device by group number."""
        return self.devices.get(group) or self.discovered_devices.get(group)
        
    def get_devices(self) -> List[Device]:
        """Get all devices."""
        all_devices = list(self.devices.values()) + list(self.discovered_devices.values())
        return sorted(all_devices, key=lambda d: d.group)
        
    def get_devices_by_type(self, device_type: DeviceType) -> List[Device]:
        """Get devices by type."""
        return [d for d in self.get_devices() if d.device_type == device_type]
        
    def get_device_by_name(self, name: str) -> Optional[Device]:
        """Get device by name."""
        for device in self.get_devices():
            if device.name == name:
                return device
        return None
        
    def add_device(self, device: Device):
        """Add a device."""
        self.devices[device.group] = device
        self.logger.info(f"Added device: {device.name} (group {device.group})")
        
    def remove_device(self, group: int):
        """Remove a device."""
        if group in self.devices:
            device = self.devices.pop(group)
            self.logger.info(f"Removed device: {device.name} (group {group})")
            
        if group in self.discovered_devices:
            device = self.discovered_devices.pop(group)
            self.logger.info(f"Removed discovered device: {device.name} (group {group})")
            
    def get_template(self, name: str) -> Optional[DeviceTemplate]:
        """Get device template by name."""
        return self.templates.get(name)
        
    def get_templates(self) -> List[DeviceTemplate]:
        """Get all device templates."""
        return list(self.templates.values())
        
    def is_dimmable(self, group: int) -> bool:
        """Check if device is dimmable."""
        device = self.get_device(group)
        return device.dimmable if device else False
        
    def get_device_icon(self, group: int) -> str:
        """Get device icon."""
        device = self.get_device(group)
        return device.icon if device else "mdi:help-circle"
        
    def get_device_area(self, group: int) -> Optional[str]:
        """Get device area."""
        device = self.get_device(group)
        return device.area if device else None
        
    def get_ha_discovery_config(self, group: int) -> Optional[Dict[str, Any]]:
        """Get Home Assistant discovery configuration for device."""
        device = self.get_device(group)
        if not device:
            return None
            
        return device.to_ha_config()
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get device manager statistics."""
        device_types = {}
        for device in self.get_devices():
            device_type = device.device_type.value
            device_types[device_type] = device_types.get(device_type, 0) + 1
            
        return {
            'total_devices': len(self.devices) + len(self.discovered_devices),
            'configured_devices': len(self.devices),
            'discovered_devices': len(self.discovered_devices),
            'templates': len(self.templates),
            'device_types': device_types,
            'auto_discovery_enabled': self.auto_discovery_enabled
        } 