"""Platform for C-Bus lights."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.light import (ATTR_BRIGHTNESS, ATTR_TRANSITION,
                                            ColorMode, LightEntity,
                                            LightEntityFeature)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CBusEntity
from .cbus.coordinator import CBusCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up C-Bus light from a config entry."""
    coordinator: CBusCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    # Add initially discovered lights
    entities = []
    for group, device_info in coordinator.get_discovered_devices().items():
        if device_info.get("type") == "light":
            entities.append(CBusLight(coordinator, group, device_info))

    if entities:
        async_add_entities(entities)

    # Listen for new device discoveries
    @callback
    def _handle_device_discovered(event):
        """Handle new device discovery."""
        if event.data.get("type") == "light":
            group = event.data["group"]
            device_info = coordinator.get_discovered_devices().get(group)
            if device_info:
                async_add_entities([CBusLight(coordinator, group, device_info)])

    # Register event listener
    hass.bus.async_listen("cbus_device_discovered", _handle_device_discovered)


class CBusLight(CBusEntity, LightEntity):
    """Representation of a C-Bus light."""

    def __init__(
        self,
        coordinator: CBusCoordinator,
        group: int,
        device_info: dict[str, Any],
    ) -> None:
        """Initialize the light."""
        super().__init__(coordinator, group)
        self.device_info_data = device_info
        self._attr_name = device_info.get("name", f"C-Bus Light {group}")
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_light_{group}"

        # Set color mode and supported features
        self._attr_color_mode = ColorMode.BRIGHTNESS
        self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}

        # Check if device supports dimming
        if device_info.get("dimmable", True):
            self._attr_supported_features = LightEntityFeature.TRANSITION
        else:
            self._attr_supported_features = 0
            self._attr_color_mode = ColorMode.ONOFF
            self._attr_supported_color_modes = {ColorMode.ONOFF}

    @property
    def is_on(self) -> bool:
        """Return True if light is on."""
        state = self.coordinator.get_device_state(self.group)
        return state.get("state", False) if state else False

    @property
    def brightness(self) -> int | None:
        """Return the brightness of the light."""
        if self._attr_color_mode == ColorMode.ONOFF:
            return None

        state = self.coordinator.get_device_state(self.group)
        if state:
            # Convert from C-Bus level (0-255) to HA brightness (0-255)
            return state.get("level", 0)
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        transition = kwargs.get(ATTR_TRANSITION, 0)

        if brightness is not None:
            # Use specified brightness
            level = brightness
        elif self.is_on:
            # Light is already on, maintain current level
            current_state = self.coordinator.get_device_state(self.group)
            level = current_state.get("level", 255) if current_state else 255
        else:
            # Turn on to full brightness
            level = 255

        try:
            if transition > 0:
                await self.coordinator.async_ramp_device(
                    self.group, level, int(transition)
                )
            else:
                await self.coordinator.async_set_device_level(self.group, level)
        except Exception as ex:
            _LOGGER.error("Error turning on light %s: %s", self.group, ex)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        transition = kwargs.get(ATTR_TRANSITION, 0)

        try:
            if transition > 0:
                await self.coordinator.async_ramp_device(self.group, 0, int(transition))
            else:
                await self.coordinator.async_set_device_level(self.group, 0)
        except Exception as ex:
            _LOGGER.error("Error turning off light %s: %s", self.group, ex)

    async def async_update(self) -> None:
        """Update the light state."""
        # This is handled by the coordinator, so we don't need to do anything
        pass

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        state = self.coordinator.get_device_state(self.group)
        if not state:
            return {}

        return {
            "group": self.group,
            "last_updated": state.get("last_updated"),
            "discovered": self.device_info_data.get("discovered", False),
        }
