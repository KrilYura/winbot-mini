# Winbot Mini

**Version:** 1.0.3

A Home Assistant custom integration that controls an Ecovacs Winbot Mini window cleaner over Bluetooth (including ESPHome Bluetooth Proxies).

## Overview

Winbot Mini discovers the robot via Home Assistant Bluetooth, connects directly over BLE, and exposes a vacuum entity plus directional control buttons. No MQTT bridge or separate add-on is required.

## Features

- **Bluetooth discovery**: Finds `WINBOT*` / `Winbot*` devices via a local adapter or ESPHome Bluetooth Proxy
- **Vacuum entity**: Start, pause, and return-to-base controls with live activity state
- **Directional buttons**: Forward, backward, left, right, and spray water
- **Custom commands**: Send mapped or raw protocol commands via `vacuum.send_command`
- **UI configuration**: Setup through Home Assistant's UI
- **Local polling**: Talks to the robot on your LAN/BLE path — no cloud required

## Requirements

- Home Assistant 2024.3.0 or newer
- A Bluetooth adapter **or** an ESPHome Bluetooth Proxy in range of the Winbot Mini
- The robot powered on and advertising (name starting with `WINBOT` / `Winbot`)

## Installation

### HACS

1. Open **HACS** → **Integrations** → **⋮** → **Custom repositories**
2. Add this repository URL and set category to **Integration**
3. Install **Winbot Mini**
4. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/winbot_mini` directory to your Home Assistant's `config/custom_components/` directory.

   ```bash
   rsync -a --delete custom_components/winbot_mini/ /path/to/homeassistant/config/custom_components/winbot_mini/
   ```

2. Restart Home Assistant.

3. Add the integration through the UI:
   - Go to **Settings** → **Devices & Services**
   - Click **+ Add Integration**
   - Search for "Winbot Mini"
   - Select your discovered device

## Configuration

No YAML options. After install, pick the discovered Winbot from the config flow. Home Assistant may also prompt you when a matching Bluetooth device is found.

### Entities

| Entity | Description |
|--------|-------------|
| Vacuum | Start, pause, return home, state |
| Forward / Backward / Left / Right | Move the robot |
| Spray water | Trigger the water spray |

### Custom commands

Mapped commands via `vacuum.send_command`:

- `start`, `pause`, `return_to_base`
- `forward`, `backward`, `left`, `right`
- `sprayWater`

Raw protocol example:

```yaml
service: vacuum.send_command
target:
  entity_id: vacuum.winbot_mini
data:
  command: move
  params:
    act: forward
```

Or with explicit category/data:

```yaml
service: vacuum.send_command
target:
  entity_id: vacuum.winbot_mini
data:
  command: unused
  params:
    category: move
    data:
      act: forward
```

## Troubleshooting

### No devices found

- Power on the Winbot and keep it nearby
- Confirm an ESPHome Bluetooth Proxy (or adapter) can see a device named `WINBOT*`
- Check **Settings** → **Devices & Services** → **Bluetooth** for recent advertisements

### Config entry not ready / unavailable

- The proxy or adapter may be out of range — move closer and reload the integration
- Ensure nothing else (phone app, another client) holds an exclusive BLE connection

### Commands do nothing

- Confirm the vacuum entity is available (connected)
- Check Home Assistant logs for BLE write / disconnect errors

## Development

### Version Management

When releasing a change, bump the version in all of these files to the same value:

- `.version`
- `custom_components/winbot_mini/manifest.json` (`version` field)
- `custom_components/winbot_mini/const.py` (`VERSION` constant)
- `README.md` (`**Version:**` at the top)
- `VERSION.md` (changelog entry)

Follow [Semantic Versioning](https://semver.org/). See `.agent/workflows/update-version.md` for the full checklist.

### File Structure

```
winbot-mini/
├── custom_components/
│   └── winbot_mini/
│       ├── __init__.py          # Integration setup
│       ├── config_flow.py       # Bluetooth / UI discovery
│       ├── const.py             # Constants and version
│       ├── device.py            # BLE connection and commands
│       ├── protocol.py          # Frame encoding / decoding
│       ├── vacuum.py            # Vacuum platform
│       ├── button.py            # Directional buttons
│       ├── manifest.json        # Integration metadata
│       ├── strings.json         # Localization
│       └── translations/
├── .agent/workflows/            # Agent versioning workflow
├── .version                     # Version number
├── hacs.json
├── README.md
└── VERSION.md                   # Changelog
```

## License

MIT License — feel free to use and modify as needed.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues, questions, or feature requests, please open an issue on GitHub.
