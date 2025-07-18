"""Platform for C-Bus switches."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CBusEntity
from .const import DOMAIN
from .cbus.coordinator import CBusCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up C-Bus switch from a config entry."""
    coordinator: CBusCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    # Add initially discovered switches
    entities = []
    for group, device_info in coordinator.get_discovered_devices().items():
        if device_info.get("type") == "switch":
            entities.append(CBusSwitch(coordinator, group, device_info))
    
    if entities:
        async_add_entities(entities)
    
    # Listen for new device discoveries
    @callback
    def _handle_device_discovered(event):
        """Handle new device discovery."""
        if event.data.get("type") == "switch":
            group = event.data["group"]
            device_info = coordinator.get_discovered_devices().get(group)
            if device_info:
                async_add_entities([CBusSwitch(coordinator, group, device_info)])
    
    # Register event listener
    hass.bus.async_listen("cbus_device_discovered", _handle_device_discovered)


class CBusSwitch(CBusEntity, SwitchEntity):
    """Representation of a C-Bus switch."""

    def __init__(
        self,
        coordinator: CBusCoordinator,
        group: int,
        device_info: dict[str, Any],
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, group)
        self.device_info_data = device_info
        self._attr_name = device_info.get("name", f"C-Bus Switch {group}")
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_switch_{group}"

    @property
    def is_on(self) -> bool:
        """Return True if switch is on."""
        state = self.coordinator.get_device_state(self.group)
        return state.get("state", False) if state else False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        try:
            await self.coordinator.async_set_device_level(self.group, 255)
        except Exception as ex:
            _LOGGER.error("Error turning on switch %s: %s", self.group, ex)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        try:
            await self.coordinator.async_set_device_level(self.group, 0)
        except Exception as ex:
            _LOGGER.error("Error turning off switch %s: %s", self.group, ex)

    async def async_update(self) -> None:
        """Update the switch state."""
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