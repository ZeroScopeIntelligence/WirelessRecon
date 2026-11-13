# WirelessRecon

**WirelessRecon v1.0.0** is a Linux command-line tool for discovering nearby Wi-Fi networks and reviewing basic wireless security information visible to your own adapter.

It is intended for wireless inventory, troubleshooting, and authorized defensive learning. It does not connect to networks, bypass security, collect credentials, or disrupt wireless communications.

## Features
- Discover nearby Wi-Fi networks through NetworkManager.
- Display SSID, BSSID, channel, frequency, link rate, signal level, and advertised security mode.
- Save timestamped JSON reports.
- Python CLI with no third-party Python packages.

## Requirements
- Linux, Python 3.9+, NetworkManager (nmcli), and a supported Wi-Fi adapter.

### Do I need an external wireless adapter?
Not necessarily. Your built-in Wi-Fi adapter may work if Linux recognizes it and NetworkManager supports it. If it is unsupported or no wireless interface appears, consider a compatible USB Wi-Fi adapter. Check the exact model and hardware revision for Linux kernel/driver support and required Wi-Fi bands before purchasing.

**Virtual machines:** A guest OS usually cannot directly use the host's internal Wi-Fi radio. A USB Wi-Fi adapter passed through to the VM may be required.

## Installation
~~~bash
git clone https://github.com/ZeroScopeIntelligence/WirelessRecon.git
cd WirelessRecon
sudo apt update
sudo apt install -y python3 network-manager iw
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
Run a scan:
~~~bash
python3 src/wireless_recon.py
~~~

Use cached scan results without requesting a new scan:
~~~bash
python3 src/wireless_recon.py --no-rescan
~~~

Choose a JSON report path:
~~~bash
python3 src/wireless_recon.py --output reports/my_scan.json
~~~

Print without saving:
~~~bash
python3 src/wireless_recon.py --no-save
~~~

By default, reports are saved under reports/. The directory is created automatically.

## Troubleshooting
If no networks appear:
1. Check for a detected wireless interface with `iw dev` and `nmcli device status`.
2. Check Wi-Fi radio state with `nmcli radio wifi`.
3. If disabled, enable it with `nmcli radio wifi on`.
4. Check software/hardware blocks with `rfkill list`.
5. In a VM, check USB passthrough and guest driver support.

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
Use WirelessRecon only on devices and networks you own or are explicitly authorized to assess. It is a passive discovery and inventory utility. Do not use it to interfere with networks, bypass access controls, or access systems without permission.

## Version
- Current version: **1.0.0**
- Release: **Initial release**
- Maintainer: **RUNNINDEAD**
- Project: **ZeroScope Solutions**

## License
Copyright © 2026 RUNNINDEAD / ZeroScope Solutions. All rights reserved. See [LICENSE](LICENSE) for project terms.
