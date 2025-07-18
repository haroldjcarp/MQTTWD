"""Platform for C-Bus fans."""

from __future__ import annotations

import logging
import math
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.percentage import (
    ordered_list_item_to_percentage,
    percentage_to_ordered_list_item,
)

from . import CBusEntity
from .cbus.coordinator import CBusCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Fan speed levels
SPEED_LEVELS = ["off", "low", "medium", "high"]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up C-Bus fan from a config entry."""
    coordinator: CBusCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    # Add initially discovered fans
    entities = []
    for group, device_info in coordinator.get_discovered_devices().items():
        if device_info.get("type") == "fan":
            entities.append(CBusFan(coordinator, group, device_info))

    if entities:
        async_add_entities(entities)

    # Listen for new device discoveries
    @callback
    def _handle_device_discovered(event):
        """Handle new device discovery."""
        if event.data.get("type") == "fan":
            group = event.data["group"]
            device_info = coordinator.get_discovered_devices().get(group)
            if device_info:
                async_add_entities([CBusFan(coordinator, group, device_info)])

    # Register event listener
    hass.bus.async_listen("cbus_device_discovered", _handle_device_discovered)


class CBusFan(CBusEntity, FanEntity):
    """Representation of a C-Bus fan."""

    def __init__(
        self,
        coordinator: CBusCoordinator,
        group: int,
        device_info: dict[str, Any],
    ) -> None:
        """Initialize the fan."""
        super().__init__(coordinator, group)
        self.device_info_data = device_info
        self._attr_name = device_info.get("name", f"C-Bus Fan {group}")
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_fan_{group}"

        # Set fan features based on device capabilities
        if device_info.get("dimmable", True):
            self._attr_supported_features = (
                FanEntityFeature.SET_SPEED | FanEntityFeature.PRESET_MODE
            )
            self._attr_speed_count = 100  # Support percentage-based speed
        else:
            self._attr_supported_features = FanEntityFeature.PRESET_MODE
            self._attr_speed_count = 1

        # Set preset modes
        self._attr_preset_modes = ["low", "medium", "high"]

    @property
    def is_on(self) -> bool:
        """Return True if fan is on."""
        state = self.coordinator.get_device_state(self.group)
        return state.get("state", False) if state else False

    @property
    def percentage(self) -> int | None:
        """Return the current speed percentage."""
        if not self.device_info_data.get("dimmable", True):
            return None

        state = self.coordinator.get_device_state(self.group)
        if state:
            # Convert from C-Bus level (0-255) to percentage (0-100)
            level = state.get("level", 0)
            return int((level / 255) * 100)
        return None

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode."""
        state = self.coordinator.get_device_state(self.group)
        if not state or not state.get("state", False):
            return None

        level = state.get("level", 0)

        # Map C-Bus levels to preset modes
        if level <= 85:  # 0-33%
            return "low"
        elif level <= 170:  # 34-66%
            return "medium"
        else:  # 67-100%
            return "high"

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the fan speed by percentage."""
        if percentage == 0:
            await self.async_turn_off()
        else:
            # Convert percentage (0-100) to C-Bus level (0-255)
            level = int((percentage / 100) * 255)
            try:
                await self.coordinator.async_set_device_level(self.group, level)
            except Exception as ex:
                _LOGGER.error("Error setting fan %s speed: %s", self.group, ex)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the fan preset mode."""
        preset_to_level = {
            "low": 85,  # ~33%
            "medium": 170,  # ~66%
            "high": 255,  # 100%
        }

        level = preset_to_level.get(preset_mode, 255)
        try:
            await self.coordinator.async_set_device_level(self.group, level)
        except Exception as ex:
            _LOGGER.error("Error setting fan %s preset: %s", self.group, ex)

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn the fan on."""
        if percentage is not None:
            await self.async_set_percentage(percentage)
        elif preset_mode is not None:
            await self.async_set_preset_mode(preset_mode)
        else:
            # Default to medium speed
            await self.async_set_preset_mode("medium")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the fan off."""
        try:
            await self.coordinator.async_set_device_level(self.group, 0)
        except Exception as ex:
            _LOGGER.error("Error turning off fan %s: %s", self.group, ex)

    async def async_update(self) -> None:
        """Update the fan state."""
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
            "dimmable": self.device_info_data.get("dimmable", True),
        }
