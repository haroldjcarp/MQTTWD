"""Config flow for C-Bus Lights integration."""

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_MQTT_TOPIC, 
    CONF_MQTT_BROKER,
    CONF_MQTT_USER,
    CONF_MQTT_PASSWORD,
    DEFAULT_CBUS_PORT, 
    DEFAULT_MQTT_TOPIC, 
    DEFAULT_MQTT_BROKER,
    DOMAIN
)

_LOGGER = logging.getLogger(__name__)

# Configuration schema following ha-cbus2mqtt pattern
DATA_SCHEMA = vol.Schema(
    {
        # C-Bus CNI Configuration
        vol.Required(CONF_HOST, default="192.168.0.50"): str,
        vol.Required(CONF_PORT, default=DEFAULT_CBUS_PORT): int,
        
        # MQTT Configuration - matching ha-cbus2mqtt
        vol.Required(CONF_MQTT_BROKER, default=DEFAULT_MQTT_BROKER): str,
        vol.Required(CONF_MQTT_USER, default="pai"): str,
        vol.Required(CONF_MQTT_PASSWORD, default="pai"): str,
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
            # Validation following ha-cbus2mqtt pattern
            if not user_input.get(CONF_HOST):
                errors["base"] = "missing_host"
            elif not user_input.get(CONF_MQTT_USER):
                errors["base"] = "missing_mqtt_user"
            elif not user_input.get(CONF_MQTT_PASSWORD):
                errors["base"] = "missing_mqtt_password"
            else:
                # Create a unique ID based on host (like ha-cbus2mqtt)
                await self.async_set_unique_id(user_input[CONF_HOST])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"C-Bus ({user_input[CONF_HOST]})",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_import(self, user_input: dict[str, Any]) -> FlowResult:
        """Handle import from configuration.yaml."""
        return await self.async_step_user(user_input)
