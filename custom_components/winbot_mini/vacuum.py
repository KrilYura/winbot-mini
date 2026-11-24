"""Vacuum platform for Winbot Mini."""

from __future__ import annotations

from typing import Any

from homeassistant.components.vacuum import (
    StateVacuumEntity,
    VacuumActivity,
    VacuumEntityFeature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import WinbotConfigEntry
from .const import DOMAIN
from .device import WinbotDevice


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WinbotConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Winbot vacuum entity."""
    async_add_entities([WinbotVacuum(entry.runtime_data)])


class WinbotVacuum(StateVacuumEntity):
    """Representation of a Winbot Mini vacuum."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_features = (
        VacuumEntityFeature.START
        | VacuumEntityFeature.PAUSE
        | VacuumEntityFeature.RETURN_HOME
        | VacuumEntityFeature.SEND_COMMAND
        | VacuumEntityFeature.STATE
    )

    def __init__(self, device: WinbotDevice) -> None:
        self._device = device
        self._attr_unique_id = f"{device.address}_vacuum"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.address)},
            name=device.name,
            manufacturer="Ecovacs",
            model="Winbot Mini",
            connections={(CONNECTION_BLUETOOTH, device.address)},
        )
        self._unsub = device.async_add_listener(self._handle_state)

    @property
    def available(self) -> bool:
        return self._device.available

    @property
    def activity(self) -> VacuumActivity | None:
        if not self._device.available:
            return None
        return self._device.activity

    @callback
    def _handle_state(self) -> None:
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None

    async def async_start(self) -> None:
        await self._device.async_send_command("start")

    async def async_pause(self) -> None:
        await self._device.async_send_command("pause")

    async def async_return_to_base(self) -> None:
        await self._device.async_send_command("return_to_base")

    async def async_send_command(
        self,
        command: str,
        params: dict[str, Any] | list[Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Send a raw or mapped command.

        Mapped: forward/backward/left/right/start/pause/sprayWater/return_to_base
        Custom JSON-style: command='move', params={'act': 'forward'}
        Or params={'category': 'move', 'data': {'act': 'forward'}}
        """
        if isinstance(params, dict) and "category" in params and "data" in params:
            await self._device.async_send_raw(params["category"], params["data"])
            return
        if isinstance(params, dict) and command:
            await self._device.async_send_raw(command, params)
            return
        await self._device.async_send_command(command)
