# WirelessRecon

**WirelessRecon v1.1.0** is a Linux command-line tool for discovering nearby Wi-Fi networks and inspecting wireless interfaces for authorized defensive inventory and lab use.

It is intended for wireless inventory, troubleshooting, and authorized defensive learning. It does not connect to networks, bypass security, collect credentials, or disrupt wireless communications.

## Features
- Discover nearby Wi-Fi networks through NetworkManager.
- Select a specific wireless interface for discovery.
- List detected wireless interfaces, their Linux driver (when available), NetworkManager state, interface type, and reported monitor-mode capability.
- Display SSID, BSSID, channel, frequency, link rate, signal level, and advertised security mode.
- Save timestamped JSON reports, including the selected interface.
- Python CLI with no third-party Python packages.

## Requirements
- Linux, Python 3.9+, NetworkManager (nmcli), the `iw` utility, and a supported Wi-Fi adapter.
- Optional: `ethtool` for driver information.

### Do I need an external wireless adapter?
Not necessarily. Your built-in Wi-Fi adapter may work if Linux recognizes it and NetworkManager supports it. If it is unsupported or no wireless interface appears, a compatible USB Wi-Fi adapter may be needed. Check the exact model and hardware revision for Linux kernel/driver support and supported Wi-Fi bands.

**Virtual machines:** A guest OS usually cannot directly use the host's internal Wi-Fi radio. A USB Wi-Fi adapter passed through to the VM may be required.

## Installation
~~~bash
git clone https://github.com/ZeroScopeIntelligence/WirelessRecon.git
cd WirelessRecon
sudo apt update
sudo apt install -y python3 network-manager iw ethtool
~~~

Check adapter detection:
~~~bash
nmcli --version
nmcli device status
iw dev
~~~

If NetworkManager is not running on a systemd-based distribution:
~~~bash
sudo systemctl enable --now NetworkManager
~~~

## Usage

List wireless interfaces:
~~~bash
python3 src/wireless_recon.py --list-interfaces
~~~

Scan using the default NetworkManager-selected Wi-Fi device:
~~~bash
python3 src/wireless_recon.py
~~~

Select a specific wireless interface:
~~~bash
python3 src/wireless_recon.py --interface wlan1
~~~

Use cached scan results on a selected interface:
~~~bash
python3 src/wireless_recon.py --interface wlan1 --no-rescan
~~~

Choose a JSON report path:
~~~bash
python3 src/wireless_recon.py --interface wlan1 --output reports/lab_scan.json
~~~

Print without saving:
~~~bash
python3 src/wireless_recon.py --interface wlan1 --no-save
~~~

By default, reports are saved under reports/. The directory is created automatically. Replace `wlan1` with an interface name shown by `--list-interfaces`.

## Understanding monitor-mode status
The interface listing checks the wireless PHY's advertised supported interface modes using `iw`. A reported monitor-mode capability means the driver advertises that mode; it does not guarantee that every capture configuration will work. This release does not automatically change interface modes or start packet capture.

## Troubleshooting
If no wireless interfaces appear:
1. Check `iw dev` and `nmcli device status`.
2. In a VM, check USB passthrough and guest driver support.
3. Check software/hardware blocks with `rfkill list`.
4. Confirm that the correct Linux driver is installed.

If a selected interface is rejected, run `--list-interfaces` and use the exact interface name displayed. A wireless interface not managed by NetworkManager may be listed but unavailable for NetworkManager scans.

Zero discovered networks does not necessarily indicate a program error. The adapter may be blocked, unsupported, out of range, or unable to scan in its current environment.

## Project structure
~~~text
WirelessRecon/
├── README.md
├── LICENSE
├── CHANGELOG.md
├── requirements.txt
├── .gitignore
├── reports/
│   └── .gitkeep
└── src/
    └── wireless_recon.py
~~~

## Responsible use
Use WirelessRecon only on devices and networks you own or are explicitly authorized to assess. It is a passive discovery and inventory utility. Do not use it to interfere with networks, bypass access controls, or access systems without permission. Packet-capture capabilities, if added in a future release, should be used only in authorized environments and handled as potentially sensitive data.

## Version
- Current version: **1.1.0**
- Release: **Wireless interface selection**
- Maintainer: **RUNNINDEAD**
- Project: **ZeroScope Solutions**

## License
Copyright © 2026 RUNNINDEAD / ZeroScope Solutions. All rights reserved. See [LICENSE](LICENSE) for project terms.
