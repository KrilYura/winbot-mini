"""Ecovacs Winbot Mini BLE payload helpers."""

from __future__ import annotations

import json
import logging
import random
import string
from typing import Any, Literal

from .const import DEFAULT_DEVICE_ID, FRAME_END, FRAME_START

_LOGGER = logging.getLogger(__name__)

ActivityName = Literal["idle", "cleaning", "paused", "returning", "docked"]

CRC_TABLE = [
    0, 49, 98, 83, 196, 245, 166, 151, 185, 136, 219, 234, 125, 76, 31, 46,
    67, 114, 33, 16, 135, 182, 229, 212, 250, 203, 152, 169, 62, 15, 92, 109,
    134, 183, 228, 213, 66, 115, 32, 17, 63, 14, 93, 108, 251, 202, 153, 168,
    197, 244, 167, 150, 1, 48, 99, 82, 124, 77, 30, 47, 184, 137, 218, 235,
    61, 12, 95, 110, 249, 200, 155, 170, 132, 181, 230, 215, 64, 113, 34, 19,
    126, 79, 28, 45, 186, 139, 216, 233, 199, 246, 165, 148, 3, 50, 97, 80,
    187, 138, 217, 232, 127, 78, 29, 44, 2, 51, 96, 81, 198, 247, 164, 149,
    248, 201, 154, 171, 60, 13, 94, 111, 65, 112, 35, 18, 133, 180, 231, 214,
    122, 75, 24, 41, 190, 143, 220, 237, 195, 242, 161, 144, 7, 54, 101, 84,
    57, 8, 91, 106, 253, 204, 159, 174, 128, 177, 226, 211, 68, 117, 38, 23,
    252, 205, 158, 175, 56, 9, 90, 107, 69, 116, 39, 22, 129, 176, 227, 210,
    191, 142, 221, 236, 123, 74, 25, 40, 6, 55, 100, 85, 194, 243, 160, 145,
    71, 118, 37, 20, 131, 178, 225, 208, 254, 207, 156, 173, 58, 11, 88, 105,
    4, 53, 102, 87, 192, 241, 162, 147, 189, 140, 223, 238, 121, 72, 27, 42,
    193, 240, 163, 146, 5, 52, 103, 86, 120, 73, 26, 43, 188, 141, 222, 239,
    130, 179, 224, 209, 70, 119, 36, 21, 59, 10, 89, 104, 255, 206, 157, 172,
]

STATIC_PAYLOADS = {
    "init_auth": bytes.fromhex(
        "604650676574496e666f0037303531313138007131625953006a7b22626f6479223a7b2264617461223a7b2274696d657374616d70223a313737373035313132327d7d7d2a0a"
    ),
    "init_bury0": bytes.fromhex(
        "60465067657442757279446174610037303531313138007130785649006a7b22626f6479223a7b2264617461223a7b7d7d7dcd0a"
    ),
    "init_bury1": bytes.fromhex(
        "604650676574427572794461746131003730353131313800717345474a006a7b22626f6479223a7b2264617461223a7b7d7d7df90a"
    ),
    "init_bury2": bytes.fromhex(
        "604650676574427572794461746132003730353131313800717830744e006a7b22626f6479223a7b2264617461223a7b7d7d7d4c0a"
    ),
}


def calculate_checksum(data: bytearray, start: int, end: int) -> int:
    """Calculate the proprietary Ecovacs CRC-8 checksum."""
    crc = 0
    for i in range(start, end):
        crc = CRC_TABLE[crc ^ data[i]]
    if crc in (0x0A, 0x60, 0x5C):
        crc += 10
    return crc & 0xFF


def generate_msg_id() -> str:
    """Generate a message ID accepted by the robot."""
    return "q" + "".join(random.choices(string.ascii_letters + string.digits, k=4))


def build_payload(
    category: str,
    json_body: dict,
    device_id: str = DEFAULT_DEVICE_ID,
) -> bytes:
    """Build a proprietary Ecovacs Winbot BLE payload."""
    header = bytearray()
    header.append(0x60)
    header.extend(b"FP")
    header.extend(category.encode("ascii"))
    header.append(0x00)
    header.extend(device_id.encode("ascii"))
    header.append(0x00)
    header.extend(generate_msg_id().encode("ascii"))
    header.append(0x00)
    header.append(0x6A)  # 'j'

    json_str = json.dumps({"body": {"data": json_body}}, separators=(",", ":"))
    header.extend(json_str.encode("utf-8"))
    header.append(calculate_checksum(header, 3, len(header)))
    header.append(0x0A)
    return bytes(header)


def payload_for_command(command: str) -> bytes | None:
    """Map a high-level command name to a BLE payload."""
    cmd = command.strip()
    if cmd in ("forward", "backward", "left", "right"):
        return build_payload("move", {"act": cmd})
    if cmd == "start":
        return build_payload(
            "clean",
            {
                "act": "start",
                "content": {"type": "z", "border": 0},
                "direction": "normal",
            },
        )
    if cmd == "pause":
        return build_payload(
            "clean",
            {"act": "pause", "content": {"type": "z", "border": 0}},
        )
    if cmd in ("return_to_base", "return_home"):
        return build_payload("clean", {"act": "start", "content": {"type": "return"}})
    if cmd.lower() == "spraywater":
        return build_payload("sprayWater", {"direction": "auto"})
    return None


def extract_frames(buffer: bytearray) -> tuple[list[bytes], bytearray]:
    """Split a BLE notify buffer into complete `FP…\\n frames."""
    frames: list[bytes] = []
    while True:
        start = buffer.find(FRAME_START)
        if start < 0:
            return frames, bytearray()
        if start > 0:
            del buffer[:start]
        end = buffer.find(FRAME_END, len(FRAME_START))
        if end < 0:
            return frames, buffer
        frames.append(bytes(buffer[: end + 1]))
        del buffer[: end + 1]


def parse_frame(frame: bytes) -> tuple[str | None, dict[str, Any] | None]:
    """Return (category, body.data) from a Winbot BLE frame."""
    if not frame.startswith(FRAME_START):
        return None, None

    try:
        text = frame.decode("utf-8", errors="ignore")
    except Exception:  # noqa: BLE001
        return None, None

    # `FP<category>\0...
    rest = text[3:]
    category, sep, after = rest.partition("\x00")
    if not sep:
        category = rest.split("{", 1)[0].strip("\x00")
        after = rest

    json_start = after.find("{")
    if json_start < 0:
        return category or None, None

    try:
        payload = json.loads(after[json_start:].rstrip("\n"))
    except json.JSONDecodeError:
        _LOGGER.debug("Failed to parse Winbot JSON from frame: %s", text)
        return category or None, None

    body = payload.get("body") if isinstance(payload, dict) else None
    if not isinstance(body, dict):
        return category or None, None
    data = body.get("data")
    return category or None, data if isinstance(data, dict) else None


def activity_from_clean_info(data: dict[str, Any]) -> ActivityName | None:
    """Map onCleanInfo / getCleanInfo data to a vacuum activity name."""
    state = data.get("state")
    if state == "idle":
        return "idle"
    if state == "move":
        # Manual jog — don't override cleaning/idle activity.
        return None
    if state != "clean":
        return None

    clean_state = data.get("cleanState") or {}
    if not isinstance(clean_state, dict):
        return "cleaning"

    motion = clean_state.get("motionState")
    router = clean_state.get("router")
    if router == "return" and motion == "working":
        return "returning"
    if motion == "pause":
        return "paused"
    if motion == "working":
        return "cleaning"
    return "cleaning"


def activity_from_get_info(data: dict[str, Any]) -> ActivityName | None:
    """Map a getInfo reply to a vacuum activity name."""
    battery = data.get("getBatteryInfo")
    if isinstance(battery, dict) and battery.get("isCharging") == 1:
        return "docked"

    clean_info = data.get("getCleanInfo")
    if isinstance(clean_info, dict):
        return activity_from_clean_info(clean_info)
    return None
