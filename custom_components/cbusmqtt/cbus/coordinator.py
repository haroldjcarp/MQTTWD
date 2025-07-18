"""C-Bus coordinator for managing communication and state."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from ..const import (
    CONF_APPLICATION,
    CONF_HOST,
    CONF_INTERFACE_TYPE,
    CONF_MAX_RETRIES,
    CONF_MONITORING_ENABLED,
    CONF_NETWORK,
    CONF_POLL_INTERVAL,
    CONF_PORT,
    CONF_SERIAL_PORT,
    CONF_TIMEOUT,
    DOMAIN,
    EVENT_CBUS_DEVICE_DISCOVERED,
    EVENT_CBUS_STATE_CHANGED,
    INTERFACE_PCI,
    INTERFACE_SERIAL,
    INTERFACE_TCP,
    UPDATE_INTERVAL,
)
from .interface import CBusInterface

_LOGGER = logging.getLogger(__name__)


class CBusCoordinator(DataUpdateCoordinator):
    """Coordinator for C-Bus communication."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.config_entry = config_entry
        self.interface: CBusInterface | None = None
        self.connected = False
        self.device_states: Dict[int, Dict[str, Any]] = {}
        self.discovered_devices: Dict[int, Dict[str, Any]] = {}

        # Configuration
        self.interface_type = config_entry.data[CONF_INTERFACE_TYPE]
        self.host = config_entry.data.get(CONF_HOST)
        self.port = config_entry.data.get(CONF_PORT)
        self.serial_port = config_entry.data.get(CONF_SERIAL_PORT)
        self.network = config_entry.data[CONF_NETWORK]
        self.application = config_entry.data[CONF_APPLICATION]
        self.monitoring_enabled = config_entry.options.get(
            CONF_MONITORING_ENABLED, True
        )
        self.poll_interval = config_entry.options.get(CONF_POLL_INTERVAL, 30)
        self.timeout = config_entry.options.get(CONF_TIMEOUT, 5)
        self.max_retries = config_entry.options.get(CONF_MAX_RETRIES, 3)

    async def async_setup(self) -> None:
        """Set up the coordinator."""
        _LOGGER.info("Setting up C-Bus coordinator")

        # Create interface configuration
        interface_config = {
            "interface": self.interface_type,
            "network": self.network,
            "application": self.application,
            "monitoring": {
                "enabled": self.monitoring_enabled,
                "poll_interval": self.poll_interval,
                "timeout": self.timeout,
                "max_retries": self.max_retries,
            },
        }

        if self.interface_type == INTERFACE_TCP:
            interface_config.update(
                {
                    "host": self.host,
                    "port": self.port,
                }
            )
        elif self.interface_type in [INTERFACE_SERIAL, INTERFACE_PCI]:
            interface_config.update(
                {
                    "serial_port": self.serial_port,
                }
            )

        # Create and initialize interface
        self.interface = CBusInterface(interface_config)
        await self.interface.initialize()

        # Register for events
        self.interface.add_event_callback(self._handle_cbus_event)

        # Start interface
        await self.interface.start()
        self.connected = True

        _LOGGER.info("C-Bus coordinator setup complete")

    async def async_shutdown(self) -> None:
        """Shut down the coordinator."""
        _LOGGER.info("Shutting down C-Bus coordinator")

        if self.interface:
            await self.interface.stop()
            self.interface = None

        self.connected = False

    async def _async_update_data(self) -> Dict[str, Any]:
        """Update data from C-Bus."""
        if not self.connected or not self.interface:
            raise UpdateFailed("C-Bus interface not connected")

        try:
            # Test connection
            if not await self.interface.ping():
                raise UpdateFailed("C-Bus ping failed")

            # Return current device states
            return {
                "devices": self.device_states,
                "discovered": self.discovered_devices,
                "connected": self.connected,
            }

        except Exception as ex:
            _LOGGER.error("Error updating C-Bus data: %s", ex)
            raise UpdateFailed(f"Error updating C-Bus data: {ex}") from ex

    async def _handle_cbus_event(self, event: Dict[str, Any]) -> None:
        """Handle C-Bus events."""
        if event["type"] == "group_state":
            group = event["group"]
            level = event["level"]
            state = event["state"]

            # Update device state
            self.device_states[group] = {
                "level": level,
                "state": state,
                "group": group,
                "last_updated": asyncio.get_event_loop().time(),
            }

            # Discover device if not known
            if group not in self.discovered_devices:
                await self._discover_device(group)

            # Fire Home Assistant event
            self.hass.bus.async_fire(
                EVENT_CBUS_STATE_CHANGED,
                {
                    "group": group,
                    "level": level,
                    "state": state,
                },
            )

            # Notify listeners
            self.async_update_listeners()

    async def _discover_device(self, group: int) -> None:
        """Discover a new device."""
        _LOGGER.info("Discovering new C-Bus device: group %s", group)

        # Basic device info
        device_info = {
            "group": group,
            "name": f"C-Bus Group {group}",
            "type": "light",  # Default to light
            "dimmable": True,  # Assume dimmable by default
            "discovered": True,
        }

        self.discovered_devices[group] = device_info

        # Fire discovery event
        self.hass.bus.async_fire(EVENT_CBUS_DEVICE_DISCOVERED, device_info)

    async def async_set_device_level(self, group: int, level: int) -> None:
        """Set device level."""
        if not self.interface:
            raise ValueError("C-Bus interface not available")

        try:
            await self.interface.set_group_level(group, level)
            _LOGGER.debug("Set group %s to level %s", group, level)
        except Exception as ex:
            _LOGGER.error("Error setting group %s level: %s", group, ex)
            raise

    async def async_ramp_device(
        self, group: int, level: int, ramp_time: int = 0
    ) -> None:
        """Ramp device to level."""
        if not self.interface:
            raise ValueError("C-Bus interface not available")

        try:
            await self.interface.ramp_group(group, level, ramp_time)
            _LOGGER.debug(
                "Ramping group %s to level %s over %s seconds", group, level, ramp_time
            )
        except Exception as ex:
            _LOGGER.error("Error ramping group %s: %s", group, ex)
            raise

    async def async_sync_device(self, group: int) -> None:
        """Sync device state."""
        if not self.interface:
            raise ValueError("C-Bus interface not available")

        try:
            await self.interface.get_group_level(group)
            _LOGGER.debug("Syncing group %s", group)
        except Exception as ex:
            _LOGGER.error("Error syncing group %s: %s", group, ex)
            raise

    async def async_refresh_devices(self) -> None:
        """Refresh all devices."""
        if not self.interface:
            raise ValueError("C-Bus interface not available")

        try:
            # Poll all known devices
            for group in list(self.device_states.keys()):
                await self.async_sync_device(group)

            _LOGGER.debug("Refreshed all devices")
        except Exception as ex:
            _LOGGER.error("Error refreshing devices: %s", ex)
            raise

    def get_device_state(self, group: int) -> Dict[str, Any] | None:
        """Get device state."""
        return self.device_states.get(group)

    def get_discovered_devices(self) -> Dict[int, Dict[str, Any]]:
        """Get discovered devices."""
        return self.discovered_devices.copy()

    def is_device_discovered(self, group: int) -> bool:
        """Check if device is discovered."""
        return group in self.discovered_devices

    async def async_add_listener(self, update_callback) -> None:
        """Add update listener."""
        return self.async_add_listener(update_callback)
