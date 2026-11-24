"""BLE client for Ecovacs Winbot Mini."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from typing import Any

from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection
from homeassistant.components.vacuum import VacuumActivity

from .const import (
    CONNECT_TIMEOUT,
    GATT_NOTIFY_UUIDS,
    GATT_WRITE_UUID,
    RECONNECT_DELAY,
    STATUS_POLL_INTERVAL,
)
from .protocol import (
    STATIC_PAYLOADS,
    ActivityName,
    activity_from_clean_info,
    activity_from_get_info,
    build_payload,
    extract_frames,
    parse_frame,
    payload_for_command,
)

_LOGGER = logging.getLogger(__name__)

_ACTIVITY_MAP: dict[ActivityName, VacuumActivity] = {
    "idle": VacuumActivity.IDLE,
    "cleaning": VacuumActivity.CLEANING,
    "paused": VacuumActivity.PAUSED,
    "returning": VacuumActivity.RETURNING,
    "docked": VacuumActivity.DOCKED,
}


class WinbotDevice:
    """Maintains a BLE connection to a Winbot Mini."""

    def __init__(self, address: str, name: str) -> None:
        self.address = address
        self.name = name
        self.activity = VacuumActivity.IDLE
        self._ble_device: BLEDevice | None = None
        self._client: BleakClientWithServiceCache | None = None
        self._connect_lock = asyncio.Lock()
        self._cmd_lock = asyncio.Lock()
        self._connected = False
        self._initialized = False
        self._shutting_down = False
        self._maintain_task: asyncio.Task | None = None
        self._poll_task: asyncio.Task | None = None
        self._listeners: list[Callable[[], None]] = []
        self._rx_buffer = bytearray()
        self._loop: asyncio.AbstractEventLoop | None = None

    @property
    def available(self) -> bool:
        """Return True when connected and initialized."""
        return self._connected and self._initialized

    def set_ble_device(self, ble_device: BLEDevice) -> None:
        """Update the BLEDevice used for connections (proxy/adapter path)."""
        self._ble_device = ble_device

    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Register a listener for connection/activity changes."""
        self._listeners.append(listener)

        def _remove() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return _remove

    def _notify_listeners(self) -> None:
        for listener in list(self._listeners):
            listener()

    def _set_activity(
        self, activity: VacuumActivity | ActivityName | None
    ) -> None:
        if isinstance(activity, str):
            activity = _ACTIVITY_MAP.get(activity)
        if activity is None or activity == self.activity:
            return
        _LOGGER.info("%s: activity %s -> %s", self.name, self.activity, activity)
        self.activity = activity
        self._notify_listeners()

    def _on_disconnect(self, _client: Any) -> None:
        if self._shutting_down:
            return
        _LOGGER.warning("%s: BLE disconnected", self.name)
        self._connected = False
        self._initialized = False
        self._rx_buffer.clear()
        self._notify_listeners()

    async def async_start(self) -> None:
        """Start the background reconnect and status poll loops."""
        self._loop = asyncio.get_running_loop()
        if self._maintain_task is None:
            self._maintain_task = asyncio.create_task(self._maintain_connection())
        if self._poll_task is None:
            self._poll_task = asyncio.create_task(self._poll_status())

    async def async_stop(self) -> None:
        """Stop reconnecting and disconnect."""
        self._shutting_down = True
        for task_name in ("_maintain_task", "_poll_task"):
            task: asyncio.Task | None = getattr(self, task_name)
            if task is not None:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                setattr(self, task_name, None)
        await self._disconnect()

    async def _maintain_connection(self) -> None:
        while not self._shutting_down:
            if not self.available:
                try:
                    await self.async_connect()
                except Exception as err:  # noqa: BLE001
                    _LOGGER.warning("%s: connect failed: %s", self.name, err)
            await asyncio.sleep(RECONNECT_DELAY)

    async def _poll_status(self) -> None:
        """Periodically request getInfo so button-started cleans sync to HA."""
        while not self._shutting_down:
            await asyncio.sleep(STATUS_POLL_INTERVAL)
            if not self.available:
                continue
            try:
                await self.async_request_status()
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("%s: status poll failed: %s", self.name, err)

    async def async_connect(self) -> None:
        """Connect, subscribe, and run the init sequence."""
        if self._ble_device is None:
            raise BleakError(f"No BLE device resolved for {self.address}")

        async with self._connect_lock:
            if self.available:
                return

            _LOGGER.info("%s: Connecting via HA Bluetooth stack", self.name)
            self._rx_buffer.clear()
            client = await establish_connection(
                BleakClientWithServiceCache,
                self._ble_device,
                self.name,
                self._on_disconnect,
                use_services_cache=True,
                max_attempts=4,
            )
            self._client = client
            self._connected = True
            self._loop = asyncio.get_running_loop()

            for uuid in GATT_NOTIFY_UUIDS:
                try:
                    await client.start_notify(uuid, self._notification_handler)
                except BleakError:
                    _LOGGER.debug("%s: notify UUID %s unavailable", self.name, uuid)

            await asyncio.sleep(1)
            for init_cmd in ("init_auth", "init_bury0", "init_bury1", "init_bury2"):
                await client.write_gatt_char(
                    GATT_WRITE_UUID,
                    STATIC_PAYLOADS[init_cmd],
                    response=False,
                )
                await asyncio.sleep(1)

            self._initialized = True
            _LOGGER.info("%s: Connected and initialized", self.name)
            self._notify_listeners()

    async def _disconnect(self) -> None:
        client = self._client
        self._client = None
        self._connected = False
        self._initialized = False
        self._rx_buffer.clear()
        if client is not None:
            try:
                await client.disconnect()
            except BleakError as err:
                _LOGGER.debug("%s: disconnect error: %s", self.name, err)
        self._notify_listeners()

    def _notification_handler(self, _sender: Any, data: bytearray) -> None:
        self._rx_buffer.extend(data)
        frames, self._rx_buffer = extract_frames(self._rx_buffer)
        for frame in frames:
            self._handle_frame(frame)

    def _handle_frame(self, frame: bytes) -> None:
        category, data = parse_frame(frame)
        if data is None:
            _LOGGER.debug("%s: unparsed frame: %s", self.name, frame.hex())
            return

        _LOGGER.debug("%s: frame category=%s data=%s", self.name, category, data)

        activity: VacuumActivity | None = None
        if category == "onCleanInfo":
            activity = activity_from_clean_info(data)
        elif category == "getInfo":
            activity = activity_from_get_info(data)
        elif category is None:
            # Some firmware replies omit a clean category parse; still try clean info.
            if "state" in data and "cleanState" in data:
                activity = activity_from_clean_info(data)
            elif "getCleanInfo" in data or "getBatteryInfo" in data:
                activity = activity_from_get_info(data)

        if activity is not None:
            # Bleak may call this from another thread; hop onto the HA loop.
            loop = self._loop
            if loop is not None and loop.is_running():
                loop.call_soon_threadsafe(self._set_activity, activity)
            else:
                self._set_activity(activity)

    async def async_request_status(self) -> None:
        """Ask the robot for a fresh getInfo snapshot."""
        await self._async_write(
            build_payload("getInfo", {"timestamp": int(time.time())})
        )

    async def async_send_command(self, command: str) -> None:
        """Send a high-level command to the robot."""
        payload = payload_for_command(command)
        if payload is None:
            raise ValueError(f"Unknown command: {command}")
        await self._async_write(payload)
        # Optimistic UI until onCleanInfo arrives.
        optimistic = {
            "start": VacuumActivity.CLEANING,
            "pause": VacuumActivity.PAUSED,
            "return_to_base": VacuumActivity.RETURNING,
            "return_home": VacuumActivity.RETURNING,
        }.get(command.strip())
        if optimistic is not None:
            self._set_activity(optimistic)

    async def async_send_raw(self, category: str, data: dict) -> None:
        """Send a custom category/data payload."""
        await self._async_write(build_payload(category, data))

    async def _async_write(self, payload: bytes) -> None:
        async with self._cmd_lock:
            if not self.available or self._client is None:
                await self.async_connect()
            if self._client is None or not self._client.is_connected:
                raise BleakError(f"{self.name} is not connected")
            async with asyncio.timeout(CONNECT_TIMEOUT):
                await self._client.write_gatt_char(
                    GATT_WRITE_UUID,
                    payload,
                    response=False,
                )
            _LOGGER.debug("%s: wrote %s", self.name, payload.hex())
