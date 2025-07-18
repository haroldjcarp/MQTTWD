"""Config flow for C-Bus Lights integration."""

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_MQTT_TOPIC, DEFAULT_CBUS_PORT, DEFAULT_MQTT_TOPIC, DOMAIN

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default="192.168.1.100"): str,
        vol.Required(CONF_PORT, default=DEFAULT_CBUS_PORT): int,
        vol.Required(CONF_MQTT_TOPIC, default=DEFAULT_MQTT_TOPIC): str,
    }
)


class CBusLightsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for C-Bus Lights."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Simple validation - just check that required fields are present
            if not user_input.get(CONF_HOST):
                errors["base"] = "missing_host"
            else:
                # Create a unique ID based on host
                await self.async_set_unique_id(user_input[CONF_HOST])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"C-Bus Lights ({user_input[CONF_HOST]})",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors,
        )
