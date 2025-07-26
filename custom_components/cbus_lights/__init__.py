"""C-Bus Lights integration - following ha-cbus2mqtt patterns."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    MQTT_TOPIC_GETALL,
    MQTT_TOPIC_GETTREE,
    CBUS_DEFAULT_NETWORK,
    CBUS_DEFAULT_APPLICATION,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.LIGHT]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the C-Bus Lights component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up C-Bus Lights from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # Setup platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services after platforms are loaded
    await async_setup_services(hass, entry)

    return True


async def async_setup_services(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Register C-Bus services - following ha-cbus2mqtt patterns."""
    
    # Enhanced discovery service with feedback
    async def enhanced_discovery_service(call: ServiceCall) -> None:
        """Enhanced C-Bus light discovery with visible feedback."""
        _LOGGER.info("🚀 ENHANCED C-BUS DISCOVERY STARTED")
        
        try:
            from homeassistant.components import mqtt
            
            # Step 1: Get network tree
            gettree_topic = MQTT_TOPIC_GETTREE.format(CBUS_DEFAULT_NETWORK)
            await mqtt.async_publish(hass, gettree_topic, "", 1)
            _LOGGER.info(f"📤 Step 1: Network tree requested → {gettree_topic}")
            
            # Step 2: Get all lights  
            getall_topic = MQTT_TOPIC_GETALL.format(CBUS_DEFAULT_NETWORK, CBUS_DEFAULT_APPLICATION)
            await mqtt.async_publish(hass, getall_topic, "", 1)
            _LOGGER.info(f"📤 Step 2: All lights requested → {getall_topic}")
            
            # Step 3: Comprehensive group testing
            _LOGGER.info("📤 Step 3: Testing individual groups 1-255...")
            
            import asyncio
            
            # Test in smaller batches for better feedback
            test_ranges = [
                (1, 25, "Common residential"),
                (26, 50, "Extended residential"), 
                (51, 75, "Commercial range 1"),
                (76, 100, "Commercial range 2"),
                (101, 125, "Large installation 1"),
                (126, 150, "Large installation 2"),
                (151, 200, "Very large installation"),
                (201, 255, "Maximum C-Bus range"),
            ]
            
            for start, end, description in test_ranges:
                _LOGGER.info(f"🔍 Testing groups {start}-{end} ({description})...")
                
                # Send status queries for this range
                for group in range(start, end + 1):
                    query_topic = f"cbus/write/{CBUS_DEFAULT_NETWORK}/{CBUS_DEFAULT_APPLICATION}/{group}/switch"
                    await mqtt.async_publish(hass, query_topic, "STATUS", 1)
                    await asyncio.sleep(0.02)  # 20ms between queries
                
                # Short delay between ranges for system to respond
                await asyncio.sleep(0.5)
                
            _LOGGER.info("✅ ENHANCED DISCOVERY COMPLETED")
            _LOGGER.info("👀 Check Settings → Devices & Services → Entities for new lights!")
            _LOGGER.info("📊 Monitor logs for discovery progress...")
            
            # Create persistent notification in HA
            await hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": "🔍 C-Bus Discovery Running",
                    "message": (
                        "**Enhanced C-Bus Light Discovery Started!**\n\n"
                        "✅ Network tree requested\n"
                        "✅ All lights requested (getall)\n" 
                        "✅ Testing groups 1-255 individually\n\n"
                        "**Where to see results:**\n"
                        "• Settings → Devices & Services → Entities\n"
                        "• Settings → System → Logs\n"
                        "• New light entities will appear automatically\n\n"
                        "This notification will auto-clear in 2 minutes."
                    ),
                    "notification_id": "cbus_discovery_running",
                },
            )
            
            # Auto-clear notification after 2 minutes
            async def clear_notification():
                await asyncio.sleep(120)  # 2 minutes
                await hass.services.async_call(
                    "persistent_notification",
                    "dismiss",
                    {"notification_id": "cbus_discovery_running"},
                )
            
            hass.async_create_task(clear_notification())
            
            # Fire event with results
            hass.bus.async_fire(
                f"{DOMAIN}_enhanced_discovery_completed",
                {
                    "groups_tested": "1-255",
                    "commands_sent": ["gettree", "getall", "status_queries"],
                    "status": "completed"
                }
            )
            
        except Exception as e:
            _LOGGER.error(f"❌ Enhanced discovery failed: {e}")
            
            # Error notification
            await hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": "❌ C-Bus Discovery Failed",
                    "message": f"Discovery failed with error: {e}",
                    "notification_id": "cbus_discovery_error",
                },
            )
    
    # Get all lights service (original MQTT-based)
    async def get_all_lights_service(call: ServiceCall) -> None:
        """Request all C-Bus light states via MQTT (like ha-cbus2mqtt getall)."""
        config = hass.data[DOMAIN][entry.entry_id]
        
        _LOGGER.info("📤 Requesting all C-Bus lights via MQTT...")
        
        try:
            from homeassistant.components import mqtt
            
            # Send getall command (following cmqttd pattern: cbus/write/network/app//getall)
            getall_topic = MQTT_TOPIC_GETALL.format(CBUS_DEFAULT_NETWORK, CBUS_DEFAULT_APPLICATION)
            
            await mqtt.async_publish(
                hass,
                getall_topic,
                "",  # Empty payload for getall request 
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

    # Combined discovery service (enhanced version)
    async def discover_lights_service(call: ServiceCall) -> None:
        """Enhanced discovery combining getall, gettree, and comprehensive scanning."""
        _LOGGER.info("🎯 Starting combined C-Bus light discovery...")
        
        # Run all discovery methods
        await get_network_tree_service(call)
        await asyncio.sleep(1)  # Small delay
        await get_all_lights_service(call) 
        await asyncio.sleep(1)  # Small delay
        await enhanced_discovery_service(call)
        
        _LOGGER.info("🏁 Combined discovery sequence completed!")

    # Register all services
    hass.services.async_register(
        DOMAIN,
        "enhanced_discovery",
        enhanced_discovery_service,
        schema=None,
    )
    
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

    _LOGGER.info("✅ C-Bus services registered successfully!")


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_forward_entry_unload(entry, "light")
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        
        # Remove services
        hass.services.async_remove(DOMAIN, "enhanced_discovery")
        hass.services.async_remove(DOMAIN, "get_all_lights") 
        hass.services.async_remove(DOMAIN, "get_network_tree")
        hass.services.async_remove(DOMAIN, "discover_lights")

    return unload_ok
