from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

import voluptuous as vol
from typing import Any, Dict, Optional
import logging

from . import api
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("email"): str,
        vol.Required("password"): str,
    }
)

class FlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""

        errors = {}
        if user_input is not None:
            try:
                await api.TPLinkCloud().login(user_input["email"], user_input["password"])
            except api.InvalidCredentials:
                errors["base"] = "invalid_credentials"
            except api.CannotConnect:
                errors["base"] = "cannot_connect"
            except:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title="TP-Link Cloud", data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class OptionsFlowHandler(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            pass
        
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required("email"): str,
                vol.Required("password"): str
            }),
        )