"""The C-Bus MQTT Bridge integration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import homeassistant.helpers.config_validation as cv
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .cbus.coordinator import CBusCoordinator
from .const import (
    CONF_APPLICATION,
    CONF_INTERFACE_TYPE,
    CONF_MAX_RETRIES,
    CONF_MONITORING_ENABLED,
    CONF_NETWORK,
    CONF_POLL_INTERVAL,
    CONF_SERIAL_PORT,
    CONF_TIMEOUT,
    DEVICE_MANUFACTURER,
    DEVICE_MODEL,
    DOMAIN,
    SUPPORTED_DEVICE_TYPES,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.LIGHT, Platform.SWITCH, Platform.FAN]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up C-Bus MQTT Bridge from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Create coordinator
    coordinator = CBusCoordinator(hass, entry)

    try:
        await coordinator.async_setup()
    except Exception as ex:
        _LOGGER.error("Error setting up C-Bus coordinator: %s", ex)
        raise ConfigEntryNotReady from ex

    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    await _async_register_services(hass, coordinator)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()

    return unload_ok


async def _async_register_services(
    hass: HomeAssistant, coordinator: CBusCoordinator
) -> None:
    """Register integration services."""

    async def async_sync_device(call) -> None:
        """Sync a specific device."""
        group = call.data.get("group")
        if group is not None:
            await coordinator.async_sync_device(group)

    async def async_refresh_devices(call) -> None:
        """Refresh all devices."""
        await coordinator.async_refresh_devices()

    async def async_set_level(call) -> None:
        """Set device level."""
        group = call.data.get("group")
        level = call.data.get("level")
        if group is not None and level is not None:
            await coordinator.async_set_device_level(group, level)

    async def async_ramp_to_level(call) -> None:
        """Ramp device to level."""
        group = call.data.get("group")
        level = call.data.get("level")
        ramp_time = call.data.get("ramp_time", 0)
        if group is not None and level is not None:
            await coordinator.async_ramp_device(group, level, ramp_time)

    # Register services
    hass.services.async_register(DOMAIN, "sync_device", async_sync_device)
    hass.services.async_register(DOMAIN, "refresh_devices", async_refresh_devices)
    hass.services.async_register(DOMAIN, "set_level", async_set_level)
    hass.services.async_register(DOMAIN, "ramp_to_level", async_ramp_to_level)


class CBusEntity(Entity):
    """Base class for C-Bus entities."""

    def __init__(self, coordinator: CBusCoordinator, group: int) -> None:
        """Initialize the entity."""
        self.coordinator = coordinator
        self.group = group
        self._attr_should_poll = False
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{group}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={
                (DOMAIN, f"{self.coordinator.config_entry.entry_id}_{self.group}")
            },
            name=f"C-Bus Group {self.group}",
            manufacturer=DEVICE_MANUFACTURER,
            model=DEVICE_MODEL,
            via_device=(DOMAIN, self.coordinator.config_entry.entry_id),
        )

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.connected

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def async_will_remove_from_hass(self) -> None:
        """When entity will be removed from hass."""
        pass
