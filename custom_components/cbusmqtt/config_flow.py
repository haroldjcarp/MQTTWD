"""Config flow for C-Bus MQTT Bridge integration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.core import callback

from .const import (CONF_APPLICATION, CONF_INTERFACE_TYPE, CONF_MAX_RETRIES,
                    CONF_MONITORING_ENABLED, CONF_NETWORK, CONF_POLL_INTERVAL,
                    CONF_SERIAL_PORT, CONF_TIMEOUT, DEFAULT_APPLICATION,
                    DEFAULT_MAX_RETRIES, DEFAULT_NAME, DEFAULT_NETWORK,
                    DEFAULT_POLL_INTERVAL, DEFAULT_PORT, DEFAULT_TIMEOUT,
                    DOMAIN, INTERFACE_PCI, INTERFACE_SERIAL, INTERFACE_TCP,
                    INTERFACE_TYPES)

_LOGGER = logging.getLogger(__name__)

# Base schema for interface selection
INTERFACE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_INTERFACE_TYPE, default=INTERFACE_TCP): vol.In(
            INTERFACE_TYPES
        ),
        vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
    }
)

# TCP interface schema
TCP_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Required(CONF_NETWORK, default=DEFAULT_NETWORK): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=255)
        ),
        vol.Required(CONF_APPLICATION, default=DEFAULT_APPLICATION): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=255)
        ),
    }
)

# Serial interface schema
SERIAL_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SERIAL_PORT, default="/dev/ttyUSB0"): str,
        vol.Required(CONF_NETWORK, default=DEFAULT_NETWORK): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=255)
        ),
        vol.Required(CONF_APPLICATION, default=DEFAULT_APPLICATION): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=255)
        ),
    }
)

# PCI interface schema
PCI_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SERIAL_PORT, default="/dev/ttyUSB0"): str,
        vol.Required(CONF_NETWORK, default=DEFAULT_NETWORK): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=255)
        ),
        vol.Required(CONF_APPLICATION, default=DEFAULT_APPLICATION): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=255)
        ),
    }
)

# Advanced options schema
ADVANCED_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MONITORING_ENABLED, default=True): bool,
        vol.Required(CONF_POLL_INTERVAL, default=DEFAULT_POLL_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=5, max=300)
        ),
        vol.Required(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=30)
        ),
        vol.Required(CONF_MAX_RETRIES, default=DEFAULT_MAX_RETRIES): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=10)
        ),
    }
)


async def validate_cbus_connection(
    hass: HomeAssistant, data: dict[str, Any]
) -> dict[str, Any]:
    """Validate the C-Bus connection."""
    try:
        # Import here to avoid circular imports
        from .cbus.interface import CBusInterface

        # Create a temporary interface to test connection
        interface = CBusInterface(data)

        # Try to initialize and connect with timeout
        await asyncio.wait_for(interface.initialize(), timeout=10)
        await asyncio.wait_for(interface.connect(), timeout=10)

        # Test basic communication with timeout
        result = await asyncio.wait_for(interface.ping(), timeout=10)

        # Clean up
        await interface.disconnect()

        if not result:
            raise CannotConnect("Failed to ping C-Bus interface")

        return {"title": data[CONF_NAME]}

    except asyncio.TimeoutError:
        _LOGGER.error("Timeout validating C-Bus connection")
        raise CannotConnect("Connection timeout - check your C-Bus interface settings")
    except Exception as exc:
        _LOGGER.error("Error validating C-Bus connection: %s", exc)
        raise CannotConnect(f"Cannot connect to C-Bus: {exc}") from exc


class CBusMQTTConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for C-Bus MQTT Bridge."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return CBusMQTTOptionsFlow(config_entry)

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.interface_type: str | None = None
        self.name: str | None = None
        self.connection_data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=INTERFACE_SCHEMA,
                description_placeholders={
                    "name": DEFAULT_NAME,
                },
            )

        self.interface_type = user_input[CONF_INTERFACE_TYPE]
        self.name = user_input[CONF_NAME]

        # Check if already configured
        await self.async_set_unique_id(self.name)
        self._abort_if_unique_id_configured()

        # Move to appropriate interface configuration
        if self.interface_type == INTERFACE_TCP:
            return await self.async_step_tcp()
        elif self.interface_type == INTERFACE_SERIAL:
            return await self.async_step_serial()
        elif self.interface_type == INTERFACE_PCI:
            return await self.async_step_pci()

        return self.async_abort(reason="unknown_interface")

    async def async_step_tcp(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle TCP interface configuration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self.connection_data = {
                CONF_NAME: self.name,
                CONF_INTERFACE_TYPE: self.interface_type,
                **user_input,
            }

            try:
                info = await validate_cbus_connection(self.hass, self.connection_data)
                return await self.async_step_advanced()
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="tcp",
            data_schema=TCP_SCHEMA,
            errors=errors,
            description_placeholders={
                "interface_type": "TCP/CNI",
            },
        )

    async def async_step_serial(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle serial interface configuration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self.connection_data = {
                CONF_NAME: self.name,
                CONF_INTERFACE_TYPE: self.interface_type,
                **user_input,
            }

            try:
                info = await validate_cbus_connection(self.hass, self.connection_data)
                return await self.async_step_advanced()
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="serial",
            data_schema=SERIAL_SCHEMA,
            errors=errors,
            description_placeholders={
                "interface_type": "Serial",
            },
        )

    async def async_step_pci(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle PCI interface configuration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self.connection_data = {
                CONF_NAME: self.name,
                CONF_INTERFACE_TYPE: self.interface_type,
                **user_input,
            }

            try:
                info = await validate_cbus_connection(self.hass, self.connection_data)
                return await self.async_step_advanced()
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="pci",
            data_schema=PCI_SCHEMA,
            errors=errors,
            description_placeholders={
                "interface_type": "PCI",
            },
        )

    async def async_step_advanced(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle advanced options."""
        if user_input is None:
            return self.async_show_form(
                step_id="advanced",
                data_schema=ADVANCED_SCHEMA,
                description_placeholders={
                    "name": self.name,
                },
            )

        # Combine all configuration data
        config_data = {
            **self.connection_data,
            **user_input,
        }

        return self.async_create_entry(
            title=self.name,
            data=config_data,
        )


class CBusMQTTOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for C-Bus MQTT Bridge."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Get current options
        options = self.config_entry.options

        # Create schema with current values
        options_schema = vol.Schema(
            {
                vol.Required(
                    CONF_MONITORING_ENABLED,
                    default=options.get(CONF_MONITORING_ENABLED, True),
                ): bool,
                vol.Required(
                    CONF_POLL_INTERVAL,
                    default=options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=300)),
                vol.Required(
                    CONF_TIMEOUT, default=options.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=30)),
                vol.Required(
                    CONF_MAX_RETRIES,
                    default=options.get(CONF_MAX_RETRIES, DEFAULT_MAX_RETRIES),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=10)),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
