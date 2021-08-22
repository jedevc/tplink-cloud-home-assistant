import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.switch import SwitchEntity

from . import api
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities):
    config = hass.data[DOMAIN][config_entry.entry_id]
    email = config["email"]
    password = config["password"]

    cloud = await api.TPLinkCloud().login(email, password)
    switches = [TPLinkSwitch(device) for device in await cloud.list_devices()]
    async_add_entities(switches)


class TPLinkSwitch(SwitchEntity):
    def __init__(self, device: api.TPLinkDevice):
        self.device = device

    @property
    def should_poll(self) -> bool:
        return True
        
    async def async_update(self):
        await self.device.refresh()

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
        await self.device.set_state(1)

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        await self.device.set_state(0)