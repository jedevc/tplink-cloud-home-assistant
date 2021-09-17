import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.switch import SwitchEntity
from typing import Any, Dict

from . import api
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
    config_data = hass.data[DOMAIN][config_entry.entry_id]

    email = config_data["email"]
    password = config_data["password"]
    token = config_data["token"]

    cloud = await api.TPLinkCloud(email, password).token(token)
    try:
        devices = await cloud.list_devices()
    except api.ExpiredToken:
        await _async_new_tokens(hass, cloud, config_entry)
        devices = await cloud.list_devices()
    except:
        _LOGGER.exception("Unexpected exception")
        return
    switches = [TPLinkSwitch(device, config_entry) for device in devices]
    async_add_entities(switches, update_before_add=True)


class TPLinkSwitch(SwitchEntity):
    def __init__(self, device: api.TPLinkDevice, config: ConfigEntry):
        self.device = device
        self.config = config

    @property
    def should_poll(self) -> bool:
        return True

    async def async_update(self):
        try:
            await self.device.refresh()
        except api.ExpiredToken:
            await _async_new_tokens(self.hass, self.device.cloud, self.config)
            await self.device.refresh()
        except:
            _LOGGER.exception("Unexpected exception")

    @property
    def name(self) -> str:
        """Name of the entity."""
        return self.device.alias

    @property
    def unique_id(self) -> str:
        """Unique ID of the entity."""
        return self.device.device_id

    @property
    def is_on(self):
        """If the switch is currently on or off."""
        return self.device.state != 0

    @property
    def device_info(self):
        """Get device info"""
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self.name,
            "manufacturer": "TP-Link",
            "model": self.device.model,
            "sw_version": self.device.software,
        }

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        try:
            await self.device.set_state(1)
        except api.ExpiredToken:
            await _async_new_tokens(self.hass, self.device.cloud, self.config)
            await self.device.set_state(1)
        except:
            _LOGGER.exception("Unexpected exception")

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        try:
            await self.device.set_state(0)
        except api.ExpiredToken:
            await _async_new_tokens(self.hass, self.device.cloud, self.config)
            await self.device.set_state(0)
        except:
            _LOGGER.exception("Unexpected exception")


async def _async_new_tokens(
    hass: HomeAssistant, cloud: api.TPLinkCloud, config: ConfigEntry
):
    cloud.login()
    await hass.config_entries.async_update_entry(
        config,
        data={
            **config.data,
            "token": cloud.get_token(),
        },
    )
