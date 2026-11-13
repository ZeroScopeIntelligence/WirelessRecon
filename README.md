# WirelessRecon

**WirelessRecon v1.2.0** is a Linux command-line utility for wireless inventory and privacy-conscious packet capture on devices and networks you are authorized to assess.

## Features
- Discover nearby Wi-Fi networks through NetworkManager.
- Select a wireless interface and inspect its driver, state, type, and reported monitor-mode capability.
- Display SSID, BSSID, channel, frequency, link rate, signal level, and advertised security mode.
- Capture traffic to/from the Kali host's own IPv4 address on a selected interface.
- Save captures in PCAPNG format with a JSON metadata sidecar.
- Keep timestamped JSON wireless discovery reports.
- Regular CLI; no interactive menus and no third-party Python packages.

## Capture scope and privacy
The initial capture implementation deliberately uses a host-only IPv4 capture filter. It records packets whose source or destination is the selected Kali interface's own assigned IPv4 address. It does not enable monitor mode, capture arbitrary nearby devices, inject packets, or disrupt wireless networks. Captures may still contain sensitive information belonging to your own device; store and share them carefully. Use this feature only on your own device and authorized lab network.

This is not an 802.11 monitor-mode frame recorder. Monitor-mode capture of nearby wireless frames is not part of this release.

## Requirements
- Linux, Python 3.9+, NetworkManager (nmcli), `iw`, `iproute2`, and a supported Wi-Fi adapter.
- `dumpcap` from Wireshark tools for PCAPNG capture.
- Optional: `ethtool` for driver information.

## Installation
~~~bash
git clone https://github.com/ZeroScopeIntelligence/WirelessRecon.git
cd WirelessRecon
sudo apt update
sudo apt install -y python3 network-manager iw iproute2 ethtool wireshark-common
~~~

If the Wireshark installer asks whether non-root users may capture packets, choose according to your system's security policy. Otherwise run the capture command with the privileges required by your local dumpcap configuration. Do not run the entire project as root unnecessarily.

## Usage

List wireless interfaces:
~~~bash
python3 src/wireless_recon.py --list-interfaces
~~~

Discover nearby networks:
~~~bash
python3 src/wireless_recon.py --interface wlan0
~~~

Capture your own host's traffic for 30 seconds:
~~~bash
python3 src/wireless_recon.py --capture --interface wlan0
~~~

Set a shorter capture duration:
~~~bash
python3 src/wireless_recon.py --capture --interface wlan0 --duration 15
~~~

Choose the PCAPNG output path:
~~~bash
python3 src/wireless_recon.py --capture --interface wlan0 --duration 30 --capture-output captures/my-lab.pcapng
~~~

Capture duration is limited to 1–300 seconds. The program refuses to overwrite an existing capture. Each capture also creates a JSON metadata file beside it, for example `my-lab.pcapng.json`.

## Inspecting a capture
Open the PCAPNG file in Wireshark, or inspect its summary with:
~~~bash
capinfos captures/my-lab.pcapng
~~~

If no packets are captured, make sure the selected interface has an IPv4 address and that your own device generates ordinary network traffic during the short capture window. For example, open a page on your own device while capturing. The capture filter only includes traffic to/from that device's assigned IPv4 address.

## Troubleshooting
- Run `ip -4 addr show dev wlan0` to confirm the interface has an IPv4 address.
- Run `dumpcap -D` to confirm Wireshark can see capture interfaces.
- If dumpcap reports a permissions error, review your distribution's Wireshark capture permissions.
- Run `python3 src/wireless_recon.py --list-interfaces` to verify the interface name.
- In a VM, confirm the adapter is passed through to Kali and the guest driver is loaded.

## Project structure
~~~text
WirelessRecon/
├── README.md
├── LICENSE
├── CHANGELOG.md
├── requirements.txt
├── .gitignore
├── captures/
├── reports/
└── src/
    └── wireless_recon.py
~~~

## Responsible use
Use WirelessRecon only on your own devices and networks you are explicitly authorized to assess. PCAPNG files can contain sensitive data. Protect them, avoid publishing captures, and delete them when no longer needed.

## Version
- Current version: **1.2.0**
- Release: **Host-scoped PCAPNG capture**
- Maintainer: **RUNNINDEAD**
- Project: **ZeroScope Solutions**

## License
Copyright © 2026 RUNNINDEAD / ZeroScope Solutions. All rights reserved. See [LICENSE](LICENSE) for project terms.
