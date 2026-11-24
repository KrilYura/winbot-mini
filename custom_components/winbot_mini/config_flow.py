"""Config flow for Winbot Mini."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS

from .const import DOMAIN, LOCAL_NAME_PREFIXES


def _is_winbot(name: str | None) -> bool:
    if not name:
        return False
    upper = name.upper()
    return any(upper.startswith(prefix.upper()) for prefix in LOCAL_NAME_PREFIXES)


class WinbotMiniConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Winbot Mini."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._discovered: dict[str, BluetoothServiceInfoBleak] = {}

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle Bluetooth discovery."""
        if not discovery_info.connectable or not _is_winbot(discovery_info.name):
            return self.async_abort(reason="not_supported")

        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        self._discovery_info = discovery_info
        self.context["title_placeholders"] = {
            "name": discovery_info.name or discovery_info.address
        }
        return await self.async_step_user()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user pick a discovered Winbot."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            discovery = self._discovered[address]
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=discovery.name or address,
                data={CONF_ADDRESS: address},
            )

        current_ids = self._async_current_ids(include_ignore=False)
        if self._discovery_info is not None:
            self._discovered[self._discovery_info.address] = self._discovery_info

        for discovery in async_discovered_service_info(self.hass, connectable=True):
            if (
                discovery.address in current_ids
                or discovery.address in self._discovered
                or not _is_winbot(discovery.name)
            ):
                continue
            self._discovered[discovery.address] = discovery

        if not self._discovered:
            return self.async_abort(reason="no_devices_found")

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): vol.In(
                        {
                            info.address: f"{info.name} ({info.address})"
                            for info in self._discovered.values()
                        }
                    )
                }
            ),
        )
