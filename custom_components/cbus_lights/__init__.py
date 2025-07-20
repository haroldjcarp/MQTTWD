"""The C-Bus Lights integration."""

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .discovery import log_all_lights

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

    # Register discovery service
    async def discover_lights_service(call: ServiceCall) -> None:
        """Handle discover lights service call."""
        host = entry.data.get(CONF_HOST, "192.168.0.50")
        port = entry.data.get(CONF_PORT, 10001)
        
        _LOGGER.info(f"🔍 Starting light discovery for {host}:{port}")
        
        try:
            devices = await log_all_lights(host, port)
            
            if devices:
                _LOGGER.info(f"✅ Discovery service completed - found {len(devices)} devices")
                
                # Fire an event with discovered devices
                hass.bus.async_fire(
                    f"{DOMAIN}_devices_discovered",
                    {
                        "devices": devices,
                        "count": len(devices),
                        "host": host,
                        "port": port
                    }
                )
            else:
                _LOGGER.warning("⚠️ Discovery service completed - no devices found")
                
        except Exception as e:
            _LOGGER.error(f"❌ Error during discovery service: {e}")

    # Register scan active groups service
    async def scan_active_groups_service(call: ServiceCall) -> None:
        """Handle scan active groups service call."""
        host = entry.data.get(CONF_HOST, "192.168.0.50")
        port = entry.data.get(CONF_PORT, 10001)
        
        _LOGGER.info(f"🔍 Starting active groups scan for {host}:{port}")
        
        try:
            # Import here to avoid circular imports
            import sys
            from pathlib import Path
            
            # Add the project root to path for imports
            project_root = Path(__file__).parent.parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))
                
            from cbus.interface import CBusInterface
            
            # Create C-Bus interface
            cbus_interface = CBusInterface(host, port)
            
            # Scan for active groups
            active_groups = await cbus_interface.scan_active_groups()
            
            if active_groups:
                _LOGGER.info(f"✅ Active groups scan completed - found {len(active_groups)} active groups: {active_groups}")
                
                # Fire an event with active groups
                hass.bus.async_fire(
                    f"{DOMAIN}_active_groups_found",
                    {
                        "active_groups": active_groups,
                        "count": len(active_groups),
                        "host": host,
                        "port": port
                    }
                )
            else:
                _LOGGER.warning("⚠️ Active groups scan completed - no active groups found")
                
        except Exception as e:
            _LOGGER.error(f"❌ Error during active groups scan: {e}")
    
    # Register the services
    hass.services.async_register(
        DOMAIN,
        "discover_lights",
        discover_lights_service,
        schema=None
    )

    hass.services.async_register(
        DOMAIN,
        "scan_active_groups",
        scan_active_groups_service,
        schema=None
    )

    _LOGGER.info("C-Bus Lights integration setup complete")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Remove services
    hass.services.async_remove(DOMAIN, "discover_lights")
    hass.services.async_remove(DOMAIN, "scan_active_groups")
    
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
