# Changelog

All notable changes to the Winbot Mini integration will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.3] - 2026-03-24

### Added
- HACS support (`hacs.json`, README)
- Version management (`.version`, `VERSION.md`, `const.VERSION`, agent workflow)

### Changed
- Dual-push remotes for Bitbucket and GitHub

## [1.0.0] - 2026-03-24

### Added
- Initial release of Winbot Mini custom integration
- Bluetooth discovery via local adapter or ESPHome Bluetooth Proxy
- Vacuum entity with start, pause, return-to-base, and state
- Directional buttons: forward, backward, left, right, spray water
- Custom / raw commands via `vacuum.send_command`
- UI configuration flow

## [Unreleased]

### Planned Features
- Richer status attributes from BLE notifications
- Options flow for reconnect / poll tuning
