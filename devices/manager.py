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
        
        # Initialize CBUS interface if not already done
        if not hasattr(self, 'cbus_interface'):
            from cbus.interface import CBusInterface
            self.cbus_interface = CBusInterface(self.config)
            await self.cbus_interface.initialize()
            await self.cbus_interface.connect()
        
        # Perform device discovery
        await self.perform_device_discovery()
        
    async def perform_device_discovery(self):
        """Perform comprehensive device discovery from CBUS system."""
        self.logger.info("Starting comprehensive device discovery")
        
        try:
            # Scan for active groups first (faster)
            active_groups = await self.cbus_interface.scan_active_groups()
            self.logger.info(f"Found {len(active_groups)} active groups: {active_groups}")
            
            # Query detailed info for each active group
            for group in active_groups:
                device_info = await self.cbus_interface.query_device_info(group)
                if device_info:
                    device = self.create_device_from_discovery(device_info)
                    self.discovered_devices[group] = device
                    self.logger.info(f"Discovered: {device.name} (Group {group}, Type: {device.device_type.value})")
                    
            # If no devices found, try a more comprehensive scan
            if not self.discovered_devices:
                self.logger.info("No devices found in quick scan, performing full discovery")
                await self.full_device_discovery()
                
        except Exception as e:
            self.logger.error(f"Error during device discovery: {e}")
            # Fall back to basic discovery
            await self.fallback_discovery()
    
    async def full_device_discovery(self):
        """Perform full device discovery scan."""
        try:
            discovered_info = await self.cbus_interface.discover_devices(1, 100)  # Scan common range
            
            for group, device_info in discovered_info.items():
                device = self.create_device_from_discovery(device_info)
                self.discovered_devices[group] = device
                self.logger.info(f"Full scan discovered: {device.name} (Group {group})")
                
        except Exception as e:
            self.logger.error(f"Error during full device discovery: {e}")
    
    async def fallback_discovery(self):
        """Fallback discovery method when CBUS queries fail."""
        self.logger.info("Using fallback discovery method")
        
        # Create basic devices for common groups that might exist
        common_groups = [1, 2, 3, 4, 5, 10, 11, 12, 20, 21, 22, 30]
        
        for group in common_groups:
            device = Device(
                group=group,
                name=f"C-Bus Device {group}",
                device_type=DeviceType.LIGHT,
                area="Discovered",
                dimmable=True
            )
            self.discovered_devices[group] = device
    
    def create_device_from_discovery(self, device_info: Dict[str, Any]) -> Device:
        """Create a Device object from discovery information."""
        # Map device type string to enum
        device_type_map = {
            'light': DeviceType.LIGHT,
            'switch': DeviceType.SWITCH,
            'fan': DeviceType.FAN,
            'sensor': DeviceType.SENSOR,
            'unknown': DeviceType.LIGHT  # Default to light
        }
        
        device_type = device_type_map.get(device_info.get('type', 'light'), DeviceType.LIGHT)
        
        # Create device with discovered information
        device = Device(
            group=device_info['group'],
            name=device_info['name'],
            device_type=device_type,
            area=device_info.get('area', 'Discovered'),
            dimmable=device_info.get('dimmable', False),
            custom_attributes={
                'discovered': True,
                'last_seen': device_info.get('last_seen'),
                'current_level': device_info.get('current_level'),
                'discovery_method': 'cbus_query'
            }
        )
        
        return device
        
    async def refresh_discovery(self):
        """Refresh device discovery - useful for finding new devices."""
        self.logger.info("Refreshing device discovery")
        
        # Clear existing discovered devices
        old_count = len(self.discovered_devices)
        self.discovered_devices.clear()
        
        # Perform new discovery
        await self.perform_device_discovery()
        
        new_count = len(self.discovered_devices)
        self.logger.info(f"Discovery refresh complete: {old_count} -> {new_count} devices")
        
        return new_count
    
    async def query_device_name(self, group: int) -> Optional[str]:
        """Query device name from CBUS system."""
        try:
            if hasattr(self, 'cbus_interface'):
                return await self.cbus_interface.get_device_label(group)
            return None
        except Exception as e:
            self.logger.error(f"Error querying device name for group {group}: {e}")
            return None

    async def discover_device(self, group: int, device_type: DeviceType = DeviceType.LIGHT) -> Optional[Device]:
        """Discover and add a new device."""
        if group in self.devices:
            return self.devices[group]
            
        # Try to get real device info from CBUS
        try:
            if hasattr(self, 'cbus_interface'):
                device_info = await self.cbus_interface.query_device_info(group)
                if device_info:
                    device = self.create_device_from_discovery(device_info)
                    self.discovered_devices[group] = device
                    self.logger.info(f"Discovered new device: {device.name} (group {group})")
                    return device
        except Exception as e:
            self.logger.debug(f"CBUS query failed for group {group}: {e}")
        
        # Fall back to basic device creation
        device = Device(
            group=group,
            name=f"C-Bus Device {group}",
            device_type=device_type,
            area="Discovered",
            dimmable=(device_type in [DeviceType.LIGHT, DeviceType.FAN]),
            custom_attributes={'discovery_method': 'fallback'}
        )
        
        self.discovered_devices[group] = device
        self.logger.info(f"Created fallback device: {device.name} (group {group})")
        
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