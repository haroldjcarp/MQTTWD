"""Light platform for C-Bus Lights integration."""

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
    DOMAIN,
    MQTT_TOPIC_BUTTON_PRESS,
    MQTT_TOPIC_LIGHT_COMMAND,
    MQTT_TOPIC_LIGHT_STATE,
)

# Add import for DeviceType
from devices.manager import DeviceType

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up C-Bus lights from a config entry."""
    config = hass.data[DOMAIN][entry.entry_id]

    # Initialize device manager and discover devices
    from devices.manager import DeviceManager
    from config.config import Config
    
    # Create config from entry data
    config_data = {
        'cbus': {
            'interface': 'tcp',
            'host': config[CONF_HOST],
            'port': config[CONF_PORT],
            'network': 254,
            'application': 56,
            'monitoring': {
                'enabled': True,
                'timeout': 5
            }
        }
    }
    
    app_config = Config(config_data)
    device_manager = DeviceManager(app_config)
    
    try:
        # Initialize device manager and perform discovery
        await device_manager.initialize()
        
        # Get discovered light devices
        discovered_lights = device_manager.get_devices_by_type(DeviceType.LIGHT)
        
        if discovered_lights:
            _LOGGER.info(f"Discovered {len(discovered_lights)} light devices from C-Bus system")
            
            # Create light entities from discovered devices
            lights = []
            for device in discovered_lights:
                light = CBusLight(
                    config,
                    light_id=str(device.group),
                    name=device.name,
                    group_address=device.group,
                    dimmable=device.dimmable,
                    device_manager=device_manager
                )
                lights.append(light)
                _LOGGER.info(f"Created light entity: {device.name} (Group {device.group})")
                
            async_add_entities(lights)
        else:
            _LOGGER.warning("No light devices discovered from C-Bus system")
            
            # Fall back to creating sample lights for testing
            _LOGGER.info("Creating sample lights for testing")
            lights = [
                CBusLight(
                    config,
                    light_id="1",
                    name="Living Room",
                    group_address=1,
                    device_manager=device_manager
                ),
                CBusLight(
                    config,
                    light_id="2",
                    name="Kitchen",
                    group_address=2,
                    device_manager=device_manager
                ),
                CBusLight(
                    config,
                    light_id="3",
                    name="Bedroom",
                    group_address=3,
                    device_manager=device_manager
                ),
            ]
            async_add_entities(lights)
            
    except Exception as e:
        _LOGGER.error(f"Error during device discovery: {e}")
        
        # Fall back to basic lights if discovery fails
        _LOGGER.info("Discovery failed, creating basic sample lights")
        lights = [
            CBusLight(
                config,
                light_id="1",
                name="Living Room (Basic)",
                group_address=1,
            ),
            CBusLight(
                config,
                light_id="2",
                name="Kitchen (Basic)",
                group_address=2,
            ),
        ]
        async_add_entities(lights)


class CBusLight(LightEntity):
    """Representation of a C-Bus light."""

    def __init__(
        self, 
        config: dict, 
        light_id: str, 
        name: str, 
        group_address: int,
        dimmable: bool = True,
        device_manager=None
    ) -> None:
        """Initialize the light."""
        self._config = config
        self._light_id = light_id
        self._name = name
        self._group_address = group_address
        self._dimmable = dimmable
        self._device_manager = device_manager
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
        if self._dimmable:
            return self._brightness
        return None

    @property
    def color_mode(self) -> ColorMode:
        """Return the color mode of the light."""
        if self._dimmable:
            return ColorMode.BRIGHTNESS
        else:
            return ColorMode.ONOFF

    @property
    def supported_color_modes(self) -> set[ColorMode]:
        """Flag supported color modes."""
        if self._dimmable:
            return {ColorMode.BRIGHTNESS}
        else:
            return {ColorMode.ONOFF}

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
        _LOGGER.info(
            "Button pressed for %s, returning state: %s", self._name, self._state
        )

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
        brightness = kwargs.get(ATTR_BRIGHTNESS, 255)
        
        if self._dimmable:
            # Set brightness level
            level = int((brightness / 255) * 255)  # Convert to C-Bus range
            command_payload = {
                "state": "ON",
                "brightness": brightness,
                "level": level,
                "light_id": self._light_id,
                "group_address": self._group_address
            }
        else:
            # Simple on/off
            command_payload = {
                "state": "ON",
                "light_id": self._light_id,
                "group_address": self._group_address
            }

        await mqtt.async_publish(
            self.hass,
            self._command_topic,
            json.dumps(command_payload),
            qos=0,
        )

        # Update local state optimistically
        self._state = True
        if self._dimmable:
            self._brightness = brightness
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        command_payload = {
            "state": "OFF",
            "light_id": self._light_id,
            "group_address": self._group_address
        }

        await mqtt.async_publish(
            self.hass,
            self._command_topic,
            json.dumps(command_payload),
            qos=0,
        )

        # Update local state optimistically
        self._state = False
        self.async_write_ha_state()

    async def async_update(self) -> None:
        """Update the light state from the device manager if available."""
        if self._device_manager:
            try:
                # Try to get real device state
                device_name = await self._device_manager.query_device_name(self._group_address)
                if device_name and device_name != self._name:
                    self._name = device_name
                    _LOGGER.info(f"Updated device name: {self._name}")
            except Exception as e:
                _LOGGER.debug(f"Error updating device state: {e}")

    @property
    def device_info(self) -> dict:
        """Return device information for the light."""
        return {
            "identifiers": {(DOMAIN, f"group_{self._group_address}")},
            "name": self._name,
            "manufacturer": "Clipsal",
            "model": "C-Bus Light",
            "via_device": (DOMAIN, "cbus_bridge"),
            "suggested_area": "Discovered" if self._device_manager else "Default",
        }
