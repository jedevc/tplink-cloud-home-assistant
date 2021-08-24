from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

import voluptuous as vol
from typing import Any, Dict, Optional
import logging

from . import api
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class FlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    def __init__(self):
        self.form = {}

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        errors = {}
        if user_input is not None:
            self.form = user_input
            try:
                cloud = await api.TPLinkCloud(
                    self.form["email"], self.form["password"]
                ).login()
            except api.InvalidCredentials:
                errors["base"] = "invalid_credentials"
            except api.CannotConnect:
                errors["base"] = "cannot_connect"
            except:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                data = {**self.form, "token": cloud.get_token()}
                return self.async_create_entry(title="TP-Link Cloud", data=data)

        schema = vol.Schema(
            {
                vol.Required(
                    "email", default=self.form.get("email", vol.UNDEFINED)
                ): str,
                vol.Required(
                    "password", default=self.form.get("password", vol.UNDEFINED)
                ): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
