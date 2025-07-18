"""Light platform for C-Bus Lights integration."""
import json
import logging
from typing import Any

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
from homeassistant.components import mqtt

from .const import (
    DOMAIN,
    CONF_MQTT_TOPIC,
    MQTT_TOPIC_LIGHT_STATE,
    MQTT_TOPIC_LIGHT_COMMAND,
    MQTT_TOPIC_BUTTON_PRESS,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up C-Bus lights from a config entry."""
    config = hass.data[DOMAIN][entry.entry_id]
    
    # For now, create a sample light - in real implementation, 
    # you'd discover lights from your C-Bus system
    lights = [
        CBusLight(
            config,
            light_id="1",
            name="Living Room",
            group_address=1,
        ),
        CBusLight(
            config,
            light_id="2", 
            name="Kitchen",
            group_address=2,
        ),
        CBusLight(
            config,
            light_id="3",
            name="Bedroom",
            group_address=3,
        ),
    ]
    
    async_add_entities(lights)


class CBusLight(LightEntity):
    """Representation of a C-Bus light."""

    def __init__(self, config: dict, light_id: str, name: str, group_address: int) -> None:
        """Initialize the light."""
        self._config = config
        self._light_id = light_id
        self._name = name
        self._group_address = group_address
        self._state = False
        self._brightness = 255
        self._available = True
        
        # MQTT topics
        self._mqtt_topic = config[CONF_MQTT_TOPIC]
        self._state_topic = MQTT_TOPIC_LIGHT_STATE.format(light_id)
        self._command_topic = MQTT_TOPIC_LIGHT_COMMAND.format(light_id)
        self._button_topic = MQTT_TOPIC_BUTTON_PRESS.format(light_id)

    @property
    def name(self) -> str:
        """Return the name of the light."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"{DOMAIN}_{self._light_id}"

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        return self._state

    @property
    def brightness(self) -> int:
        """Return the brightness of the light."""
        return self._brightness

    @property
    def color_mode(self) -> ColorMode:
        """Return the color mode of the light."""
        return ColorMode.BRIGHTNESS

    @property
    def supported_color_modes(self) -> set[ColorMode]:
        """Flag supported color modes."""
        return {ColorMode.BRIGHTNESS}

    @property
    def available(self) -> bool:
        """Return if light is available."""
        return self._available

    async def async_added_to_hass(self) -> None:
        """Subscribe to MQTT topics."""
        # Subscribe to state updates
        await mqtt.async_subscribe(
            self.hass,
            self._state_topic,
            self._handle_state_message,
            qos=0,
        )
        
        # Subscribe to button presses
        await mqtt.async_subscribe(
            self.hass,
            self._button_topic,
            self._handle_button_press,
            qos=0,
        )

    @callback
    def _handle_state_message(self, msg) -> None:
        """Handle incoming state message."""
        try:
            payload = json.loads(msg.payload)
            self._state = payload.get("state", "OFF") == "ON"
            self._brightness = payload.get("brightness", 255)
            self._available = True
            self.async_write_ha_state()
        except (json.JSONDecodeError, KeyError) as err:
            _LOGGER.warning("Invalid state message: %s", err)

    @callback
    def _handle_button_press(self, msg) -> None:
        """Handle button press - return current state."""
        _LOGGER.info("Button pressed for %s, returning state: %s", self._name, self._state)
        
        # Publish current state when button is pressed
        state_payload = {
            "state": "ON" if self._state else "OFF",
            "brightness": self._brightness,
            "light_id": self._light_id,
            "name": self._name,
            "group_address": self._group_address,
        }
        
        mqtt.async_publish(
            self.hass,
            self._state_topic,
            json.dumps(state_payload),
            qos=0,
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        brightness = kwargs.get(ATTR_BRIGHTNESS, self._brightness)
        
        payload = {
            "state": "ON",
            "brightness": brightness,
            "group_address": self._group_address,
        }
        
        await mqtt.async_publish(
            self.hass,
            self._command_topic,
            json.dumps(payload),
            qos=0,
        )
        
        # Update local state
        self._state = True
        self._brightness = brightness
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        payload = {
            "state": "OFF",
            "group_address": self._group_address,
        }
        
        await mqtt.async_publish(
            self.hass,
            self._command_topic,
            json.dumps(payload),
            qos=0,
        )
        
        # Update local state
        self._state = False
        self.async_write_ha_state() 