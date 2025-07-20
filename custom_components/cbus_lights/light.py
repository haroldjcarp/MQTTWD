"""Light platform for C-Bus Lights integration - following ha-cbus2mqtt patterns."""

import json
import logging
from typing import Any

from homeassistant.components import mqtt
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import (
    CONF_MQTT_TOPIC,
    CONF_MQTT_BROKER, 
    CONF_MQTT_USER,
    CONF_MQTT_PASSWORD,
    DOMAIN,
    MQTT_TOPIC_LIGHT_STATE,
    MQTT_TOPIC_LIGHT_LEVEL,
    MQTT_TOPIC_LIGHT_COMMAND,
    MQTT_TOPIC_LIGHT_RAMP,
    MQTT_TOPIC_GETALL,
    DISCOVERY_PREFIX,
    CBUS_DEFAULT_NETWORK,
    CBUS_DEFAULT_APPLICATION,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up C-Bus lights from a config entry - following ha-cbus2mqtt pattern."""
    config = hass.data[DOMAIN][entry.entry_id]

    # Create MQTT-based light discovery manager
    manager = CBusLightDiscoveryManager(hass, config)
    
    # Subscribe to discovery topics to find lights automatically
    await manager.async_setup_discovery()
    
    # Request current state of all lights (like ha-cbus2mqtt does)
    await manager.async_request_all_lights()


class CBusLightDiscoveryManager:
    """Manages discovery of C-Bus lights via MQTT - following ha-cbus2mqtt patterns."""
    
    def __init__(self, hass: HomeAssistant, config: dict):
        """Initialize the discovery manager."""
        self.hass = hass
        self.config = config
        self.discovered_lights = {}
        self.network = CBUS_DEFAULT_NETWORK
        self.application = CBUS_DEFAULT_APPLICATION
        
    async def async_setup_discovery(self):
        """Set up MQTT discovery subscriptions."""
        # Subscribe to all C-Bus read topics for automatic discovery
        # Following cmqttd pattern: cbus/read/network/app/group/state
        discovery_topic = f"cbus/read/{self.network}/{self.application}/+/state"
        
        await mqtt.async_subscribe(
            self.hass,
            discovery_topic,
            self._async_discover_light_callback,
            1,
        )
        
        _LOGGER.info(f"🔍 Subscribed to C-Bus light discovery: {discovery_topic}")
        
    async def _async_discover_light_callback(self, msg):
        """Handle discovered light from MQTT topic."""
        try:
            # Parse topic: cbus/read/254/56/123/state
            topic_parts = msg.topic.split('/')
            if len(topic_parts) >= 6:
                network = topic_parts[2]
                application = topic_parts[3] 
                group = topic_parts[4]
                
                light_id = f"{network}_{application}_{group}"
                
                if light_id not in self.discovered_lights:
                    _LOGGER.info(f"🔍 Discovered new C-Bus light: Group {group}")
                    
                    # Create light entity
                    light = CBusLight(
                        self.config,
                        network=network,
                        application=application,
                        group=group,
                    )
                    
                    # Add to Home Assistant
                    self.hass.async_create_task(
                        self.hass.config_entries.async_add_devices([light])
                    )
                    
                    self.discovered_lights[light_id] = light
                    
        except Exception as e:
            _LOGGER.error(f"Error discovering light from {msg.topic}: {e}")
    
    async def async_request_all_lights(self):
        """Request all light states - following ha-cbus2mqtt getall pattern."""
        getall_topic = MQTT_TOPIC_GETALL.format(self.network, self.application)
        
        await mqtt.async_publish(
            self.hass,
            getall_topic,
            "",  # Empty payload for getall request
            1,
        )
        
        _LOGGER.info(f"📡 Requested all C-Bus lights: {getall_topic}")


class CBusLight(LightEntity):
    """C-Bus Light Entity - following ha-cbus2mqtt MQTT patterns."""

    def __init__(
        self,
        config: dict,
        network: str,
        application: str, 
        group: str,
    ):
        """Initialize C-Bus light."""
        self._config = config
        self._network = network
        self._application = application
        self._group = group
        
        # Entity attributes following ha-cbus2mqtt pattern
        self._attr_unique_id = f"cbus_{network}_{application}_{group}"
        self._attr_name = f"C-Bus Light {group}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"cbus_{network}_{application}")},
            "name": f"C-Bus Network {network}",
            "manufacturer": "Clipsal",
            "model": "C-Bus System",
        }
        
        # Light capabilities
        self._attr_color_mode = ColorMode.BRIGHTNESS
        self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
        self._attr_supported_features = LightEntityFeature.TRANSITION
        
        # State tracking
        self._attr_is_on = False
        self._attr_brightness = 0
        self._available = True
        
        # MQTT topics following cmqttd pattern
        self._state_topic = MQTT_TOPIC_LIGHT_STATE.format(network, application, group)
        self._level_topic = MQTT_TOPIC_LIGHT_LEVEL.format(network, application, group)  
        self._command_topic = MQTT_TOPIC_LIGHT_COMMAND.format(network, application, group)
        self._ramp_topic = MQTT_TOPIC_LIGHT_RAMP.format(network, application, group)

    async def async_added_to_hass(self):
        """Subscribe to MQTT topics when added to hass."""
        # Subscribe to state updates
        await mqtt.async_subscribe(
            self.hass,
            self._state_topic,
            self._async_state_callback,
            1,
        )
        
        await mqtt.async_subscribe(
            self.hass,
            self._level_topic,
            self._async_level_callback,
            1,
        )
        
        _LOGGER.info(f"✅ Added C-Bus Light {self._group} with topics:")
        _LOGGER.info(f"   State: {self._state_topic}")
        _LOGGER.info(f"   Level: {self._level_topic}")

    @callback
    def _async_state_callback(self, msg):
        """Handle state updates from MQTT."""
        try:
            payload = msg.payload.strip().upper()
            self._attr_is_on = payload == "ON"
            self.async_write_ha_state()
            _LOGGER.debug(f"State update - Group {self._group}: {payload}")
        except Exception as e:
            _LOGGER.error(f"Error processing state for group {self._group}: {e}")

    @callback  
    def _async_level_callback(self, msg):
        """Handle level updates from MQTT."""
        try:
            level = int(msg.payload)
            # Convert C-Bus level (0-255) to HA brightness (0-255) 
            self._attr_brightness = level
            self._attr_is_on = level > 0
            self.async_write_ha_state()
            _LOGGER.debug(f"Level update - Group {self._group}: {level}")
        except (ValueError, TypeError) as e:
            _LOGGER.error(f"Error processing level for group {self._group}: {e}")

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on - following ha-cbus2mqtt command pattern."""
        brightness = kwargs.get(ATTR_BRIGHTNESS, 255)
        
        if ATTR_BRIGHTNESS in kwargs:
            # Use ramp command for brightness control
            percent = int((brightness / 255) * 100)
            payload = str(percent)
            topic = self._ramp_topic
        else:
            # Use switch command for simple on
            payload = "ON"
            topic = self._command_topic
            
        await mqtt.async_publish(
            self.hass,
            topic,
            payload,
            1,
        )
        
        _LOGGER.debug(f"Turn on Group {self._group}: {payload} -> {topic}")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off - following ha-cbus2mqtt command pattern."""
        await mqtt.async_publish(
            self.hass,
            self._command_topic,
            "OFF", 
            1,
        )
        
        _LOGGER.debug(f"Turn off Group {self._group}")

    @property
    def available(self) -> bool:
        """Return if light is available."""
        return self._available
