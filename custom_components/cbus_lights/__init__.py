"""The C-Bus Lights integration - following ha-cbus2mqtt patterns."""

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    CONF_MQTT_BROKER,
    CONF_MQTT_USER, 
    CONF_MQTT_PASSWORD,
    CONF_MQTT_TOPIC,
    MQTT_TOPIC_GETALL,
    MQTT_TOPIC_GETTREE,
    CBUS_DEFAULT_NETWORK,
    CBUS_DEFAULT_APPLICATION,
)

_LOGGER = logging.getLogger(__name__)

# Platforms to set up - following ha-cbus2mqtt pattern
PLATFORMS = ["light"]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the C-Bus Lights component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up C-Bus Lights from a config entry - following ha-cbus2mqtt patterns."""
    # Store config data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register C-Bus services following ha-cbus2mqtt functionality
    await _async_register_services(hass, entry)

    _LOGGER.info("✅ C-Bus Lights integration setup complete")
    return True


async def _async_register_services(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Register C-Bus services - following ha-cbus2mqtt service patterns."""
    
    # Get all lights service (like ha-cbus2mqtt getall command)
    async def get_all_lights_service(call: ServiceCall) -> None:
        """Request all light states from C-Bus system."""
        config = hass.data[DOMAIN][entry.entry_id]
        
        _LOGGER.info("📡 Requesting all C-Bus light states...")
        
        try:
            from homeassistant.components import mqtt
            
            # Send getall command (following cmqttd pattern)
            getall_topic = MQTT_TOPIC_GETALL.format(
                CBUS_DEFAULT_NETWORK, 
                CBUS_DEFAULT_APPLICATION
            )
            
            await mqtt.async_publish(
                hass,
                getall_topic,
                "",  # Empty payload for getall
                1,
            )
            
            _LOGGER.info(f"✅ Sent getall request to: {getall_topic}")
            
            # Fire event for successful request
            hass.bus.async_fire(
                f"{DOMAIN}_getall_requested",
                {
                    "topic": getall_topic,
                    "network": CBUS_DEFAULT_NETWORK,
                    "application": CBUS_DEFAULT_APPLICATION,
                }
            )
            
        except Exception as e:
            _LOGGER.error(f"❌ Error requesting all lights: {e}")

    # Get network tree service (like ha-cbus2mqtt gettree command)  
    async def get_network_tree_service(call: ServiceCall) -> None:
        """Request C-Bus network tree information."""
        config = hass.data[DOMAIN][entry.entry_id]
        
        _LOGGER.info("🌳 Requesting C-Bus network tree...")
        
        try:
            from homeassistant.components import mqtt
            
            # Send gettree command (following cmqttd pattern)
            gettree_topic = MQTT_TOPIC_GETTREE.format(CBUS_DEFAULT_NETWORK)
            
            await mqtt.async_publish(
                hass,
                gettree_topic,
                "",  # Empty payload for gettree
                1,
            )
            
            _LOGGER.info(f"✅ Sent gettree request to: {gettree_topic}")
            
            # Fire event for successful request
            hass.bus.async_fire(
                f"{DOMAIN}_gettree_requested", 
                {
                    "topic": gettree_topic,
                    "network": CBUS_DEFAULT_NETWORK,
                }
            )
            
        except Exception as e:
            _LOGGER.error(f"❌ Error requesting network tree: {e}")

    # Discover lights service (combines getall + discovery)
    async def discover_lights_service(call: ServiceCall) -> None:
        """Trigger C-Bus light discovery process."""
        _LOGGER.info("🔍 Starting C-Bus light discovery...")
        
        try:
            # First get network tree
            await get_network_tree_service(call)
            
            # Then get all current states  
            await get_all_lights_service(call)
            
            _LOGGER.info("✅ C-Bus light discovery initiated")
            
        except Exception as e:
            _LOGGER.error(f"❌ Error during light discovery: {e}")

    # Register services - following ha-cbus2mqtt naming
    hass.services.async_register(
        DOMAIN,
        "get_all_lights",
        get_all_lights_service,
        schema=None,
    )

    hass.services.async_register(
        DOMAIN,
        "get_network_tree", 
        get_network_tree_service,
        schema=None,
    )
    
    hass.services.async_register(
        DOMAIN,
        "discover_lights",
        discover_lights_service,
        schema=None,
    )

    # Legacy service name for compatibility
    hass.services.async_register(
        DOMAIN,
        "scan_active_groups",
        get_all_lights_service,
        schema=None,
    )

    _LOGGER.info("✅ Registered C-Bus services: get_all_lights, get_network_tree, discover_lights")


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Remove services
    hass.services.async_remove(DOMAIN, "get_all_lights")
    hass.services.async_remove(DOMAIN, "get_network_tree") 
    hass.services.async_remove(DOMAIN, "discover_lights")
    hass.services.async_remove(DOMAIN, "scan_active_groups")
    
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
