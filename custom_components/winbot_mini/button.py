"""Button platform for Winbot Mini directional controls."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import WinbotConfigEntry
from .const import DOMAIN
from .device import WinbotDevice


@dataclass(frozen=True, kw_only=True)
class WinbotButtonDescription(ButtonEntityDescription):
    """Button description with Winbot command."""

    command: str


BUTTONS: tuple[WinbotButtonDescription, ...] = (
    WinbotButtonDescription(
        key="forward",
        translation_key="forward",
        icon="mdi:arrow-up-bold",
        command="forward",
    ),
    WinbotButtonDescription(
        key="backward",
        translation_key="backward",
        icon="mdi:arrow-down-bold",
        command="backward",
    ),
    WinbotButtonDescription(
        key="left",
        translation_key="left",
        icon="mdi:arrow-left-bold",
        command="left",
    ),
    WinbotButtonDescription(
        key="right",
        translation_key="right",
        icon="mdi:arrow-right-bold",
        command="right",
    ),
    WinbotButtonDescription(
        key="spray_water",
        translation_key="spray_water",
        icon="mdi:water",
        command="sprayWater",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WinbotConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Winbot buttons."""
    device = entry.runtime_data
    async_add_entities(
        WinbotButton(device, description) for description in BUTTONS
    )


class WinbotButton(ButtonEntity):
    """Button that sends a Winbot command."""

    _attr_has_entity_name = True
    entity_description: WinbotButtonDescription

    def __init__(
        self, device: WinbotDevice, description: WinbotButtonDescription
    ) -> None:
        self._device = device
        self.entity_description = description
        self._attr_unique_id = f"{device.address}_{description.key}"
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

    @callback
    def _handle_state(self) -> None:
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None

    async def async_press(self) -> None:
        await self._device.async_send_command(self.entity_description.command)
