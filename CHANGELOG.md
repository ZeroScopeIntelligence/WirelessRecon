# Changelog

All notable changes to WirelessRecon are documented here.

## [1.1.0] - 2026-11-13

### Added
- Wireless interface listing with `--list-interfaces`.
- Explicit interface selection for NetworkManager discovery with `--interface`.
- Interface type, NetworkManager state, driver information when ethtool is available, and reported monitor-mode capability.
- Selected interface recorded in JSON scan reports.
- Validation and helpful error output for unknown interface names.

### Notes
- Monitor-mode support is reported from the wireless PHY capabilities; this release does not change interface modes or perform packet capture.
- Existing discovery remains based on NetworkManager and nmcli.

## [1.0.0] - 2026-11-12

### Added
- Initial Linux CLI release.
- Nearby Wi-Fi discovery through NetworkManager and nmcli.
- SSID, BSSID, channel, frequency, rate, signal, and security details.
- Timestamped JSON reports.
- CLI options for rescanning, custom report paths, and disabling report output.
- Adapter and virtual-machine troubleshooting guidance.

### Scope
- Passive wireless discovery and authorized defensive inventory only.
- No credential collection, access-control bypass, or wireless disruption functionality.
