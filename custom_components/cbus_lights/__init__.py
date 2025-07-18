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
    
    # Register the service
    hass.services.async_register(
        DOMAIN,
        "discover_lights",
        discover_lights_service,
        schema=None
    )

    _LOGGER.info("C-Bus Lights integration setup complete")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Remove service
    hass.services.async_remove(DOMAIN, "discover_lights")
    
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
