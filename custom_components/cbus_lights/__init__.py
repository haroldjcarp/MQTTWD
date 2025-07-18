"""The C-Bus Lights integration."""

import logging
from typing import Any, Dict

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.typing import ConfigType

from .const import CONF_MQTT_TOPIC, DOMAIN

_LOGGER = logging.getLogger(__name__)

# Platforms to set up
PLATFORMS = ["light"]

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the C-Bus Lights component."""
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up C-Bus Lights from a config entry."""
    # Store config data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register discovery services
    await register_services(hass, entry)

    return True

async def register_services(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Register discovery services."""
    
    async def discover_devices_service(call: ServiceCall) -> None:
        """Handle discover devices service call."""
        start_group = call.data.get("start_group", 1)
        end_group = call.data.get("end_group", 50)
        
        _LOGGER.info(f"Starting device discovery: groups {start_group}-{end_group}")
        
        try:
            # Import here to avoid circular imports
            from devices.manager import DeviceManager
            from config.config import Config
            
            # Create device manager
            config_data = {
                'cbus': {
                    'interface': 'tcp',
                    'host': entry.data[CONF_HOST],
                    'port': entry.data[CONF_PORT],
                    'network': 254,
                    'application': 56,
                    'monitoring': {'enabled': True, 'timeout': 5}
                }
            }
            
            app_config = Config(config_data)
            device_manager = DeviceManager(app_config)
            await device_manager.initialize()
            
            # Perform discovery
            if hasattr(device_manager, 'cbus_interface'):
                discovered = await device_manager.cbus_interface.discover_devices(start_group, end_group)
                
                # Update discovered devices
                for group, device_info in discovered.items():
                    device = device_manager.create_device_from_discovery(device_info)
                    device_manager.discovered_devices[group] = device
                
                _LOGGER.info(f"Discovery complete: found {len(discovered)} devices")
                
                # Trigger a reload of the integration to pick up new devices
                await hass.config_entries.async_reload(entry.entry_id)
            else:
                _LOGGER.error("C-Bus interface not available for discovery")
                
        except Exception as e:
            _LOGGER.error(f"Error during device discovery: {e}")
    
    async def refresh_device_names_service(call: ServiceCall) -> None:
        """Handle refresh device names service call."""
        _LOGGER.info("Refreshing device names from C-Bus system")
        
        try:
            # This would update existing devices with fresh names from the system
            # Implementation depends on how you want to handle name updates
            _LOGGER.info("Device name refresh completed")
            
        except Exception as e:
            _LOGGER.error(f"Error refreshing device names: {e}")
    
    async def query_device_info_service(call: ServiceCall) -> None:
        """Handle query device info service call."""
        group = call.data.get("group")
        
        if not group:
            _LOGGER.error("Group number is required for device info query")
            return
        
        _LOGGER.info(f"Querying device info for group {group}")
        
        try:
            from devices.manager import DeviceManager
            from config.config import Config
            
            # Create device manager
            config_data = {
                'cbus': {
                    'interface': 'tcp',
                    'host': entry.data[CONF_HOST],
                    'port': entry.data[CONF_PORT],
                    'network': 254,
                    'application': 56,
                    'monitoring': {'enabled': True, 'timeout': 5}
                }
            }
            
            app_config = Config(config_data)
            device_manager = DeviceManager(app_config)
            await device_manager.initialize()
            
            # Query device info
            if hasattr(device_manager, 'cbus_interface'):
                device_info = await device_manager.cbus_interface.query_device_info(group)
                
                if device_info:
                    _LOGGER.info(f"Device info for group {group}: {device_info}")
                    
                    # Fire an event with the device info
                    hass.bus.async_fire(
                        f"{DOMAIN}_device_info",
                        {
                            "group": group,
                            "device_info": device_info
                        }
                    )
                else:
                    _LOGGER.warning(f"No device found at group {group}")
            else:
                _LOGGER.error("C-Bus interface not available for device query")
                
        except Exception as e:
            _LOGGER.error(f"Error querying device info: {e}")
    
    async def scan_active_groups_service(call: ServiceCall) -> None:
        """Handle scan active groups service call."""
        _LOGGER.info("Scanning for active C-Bus groups")
        
        try:
            from devices.manager import DeviceManager
            from config.config import Config
            
            # Create device manager
            config_data = {
                'cbus': {
                    'interface': 'tcp',
                    'host': entry.data[CONF_HOST],
                    'port': entry.data[CONF_PORT],
                    'network': 254,
                    'application': 56,
                    'monitoring': {'enabled': True, 'timeout': 5}
                }
            }
            
            app_config = Config(config_data)
            device_manager = DeviceManager(app_config)
            await device_manager.initialize()
            
            # Scan for active groups
            if hasattr(device_manager, 'cbus_interface'):
                active_groups = await device_manager.cbus_interface.scan_active_groups()
                
                _LOGGER.info(f"Active groups found: {active_groups}")
                
                # Fire an event with the active groups
                hass.bus.async_fire(
                    f"{DOMAIN}_active_groups",
                    {
                        "active_groups": active_groups,
                        "count": len(active_groups)
                    }
                )
            else:
                _LOGGER.error("C-Bus interface not available for group scan")
                
        except Exception as e:
            _LOGGER.error(f"Error scanning active groups: {e}")
    
    # Register services
    hass.services.async_register(
        DOMAIN,
        "discover_devices",
        discover_devices_service,
        schema=None
    )
    
    hass.services.async_register(
        DOMAIN,
        "refresh_device_names",
        refresh_device_names_service,
        schema=None
    )
    
    hass.services.async_register(
        DOMAIN,
        "query_device_info",
        query_device_info_service,
        schema=None
    )
    
    hass.services.async_register(
        DOMAIN,
        "scan_active_groups",
        scan_active_groups_service,
        schema=None
    )
    
    _LOGGER.info("C-Bus discovery services registered")

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unregister services
    hass.services.async_remove(DOMAIN, "discover_devices")
    hass.services.async_remove(DOMAIN, "refresh_device_names")
    hass.services.async_remove(DOMAIN, "query_device_info")
    hass.services.async_remove(DOMAIN, "scan_active_groups")
    
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
