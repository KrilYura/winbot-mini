"""Winbot Mini custom integration."""

from __future__ import annotations

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady

from .device import WinbotDevice

PLATFORMS: list[Platform] = [Platform.VACUUM, Platform.BUTTON]

type WinbotConfigEntry = ConfigEntry[WinbotDevice]


async def async_setup_entry(hass: HomeAssistant, entry: WinbotConfigEntry) -> bool:
    """Set up Winbot Mini from a config entry."""
    address: str = entry.data[CONF_ADDRESS]
    ble_device = bluetooth.async_ble_device_from_address(hass, address, True)
    if ble_device is None:
        raise ConfigEntryNotReady(
            f"Could not find Winbot Mini at {address}. "
            "Is an ESPHome Bluetooth Proxy (or adapter) in range?"
        )

    device = WinbotDevice(address=address, name=entry.title or address)
    device.set_ble_device(ble_device)

    @callback
    def _async_update_ble(
        service_info: bluetooth.BluetoothServiceInfoBleak,
        _change: bluetooth.BluetoothChange,
    ) -> None:
        device.set_ble_device(service_info.device)

    entry.async_on_unload(
        bluetooth.async_register_callback(
            hass,
            _async_update_ble,
            {"address": address},
            bluetooth.BluetoothScanningMode.ACTIVE,
        )
    )

    try:
        await device.async_connect()
    except Exception as err:
        raise ConfigEntryNotReady(f"Unable to connect to Winbot Mini: {err}") from err

    await device.async_start()
    entry.runtime_data = device
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: WinbotConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.async_stop()
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: WinbotConfigEntry) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
