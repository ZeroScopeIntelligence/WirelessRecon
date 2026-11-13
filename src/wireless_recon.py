#!/usr/bin/env python3
"""WirelessRecon: Linux Wi-Fi discovery and privacy-conscious packet capture."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

FIELDS = ("SSID", "BSSID", "CHAN", "FREQ", "RATE", "SIGNAL", "SECURITY")
VERSION = "1.2.0"
MAX_CAPTURE_SECONDS = 300


class WirelessReconError(RuntimeError):
    """Raised when wireless discovery or capture cannot be completed."""


def run_command(command: list[str], timeout: int = 15) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command, check=False, capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired as exc:
        raise WirelessReconError(f"Command timed out: {command[0]}") from exc
    except OSError as exc:
        raise WirelessReconError(f"Unable to run {command[0]}: {exc}") from exc


def split_nmcli_fields(line: str) -> list[str]:
    """Split nmcli terse output on unescaped colons."""
    values: list[str] = []
    current: list[str] = []
    escaped = False
    for char in line.rstrip("\n"):
        if escaped:
            current.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == ":":
            values.append("".join(current))
            current = []
        else:
            current.append(char)
    if escaped:
        current.append("\\")
    values.append("".join(current))
    return values


def get_nmcli_device_states() -> dict[str, str]:
    if shutil.which("nmcli") is None:
        return {}
    result = run_command([
        "nmcli", "--terse", "--escape", "yes",
        "--fields", "DEVICE,TYPE,STATE", "device", "status",
    ])
    states: dict[str, str] = {}
    if result.returncode == 0:
        for line in result.stdout.splitlines():
            fields = split_nmcli_fields(line)
            if len(fields) >= 3 and fields[1] == "wifi":
                states[fields[0]] = fields[2]
    return states


def get_wireless_interfaces() -> list[dict[str, str]]:
    """Return wireless interfaces exposed by the Linux nl80211 subsystem."""
    if shutil.which("iw") is None:
        raise WirelessReconError("'iw' was not found. Install it with: sudo apt install iw")
    result = run_command(["iw", "dev"])
    if result.returncode != 0:
        raise WirelessReconError(result.stderr.strip() or "Unable to inspect wireless interfaces.")

    interfaces: list[dict[str, str]] = []
    current_phy = ""
    current: dict[str, str] | None = None
    for line in result.stdout.splitlines():
        stripped = line.strip()
        phy_match = re.match(r"phy#(\d+)", stripped)
        if phy_match:
            current_phy = f"phy{phy_match.group(1)}"
        elif stripped.startswith("Interface "):
            if current:
                interfaces.append(current)
            current = {
                "name": stripped.split(None, 1)[1],
                "phy": current_phy or "unknown",
                "type": "unknown",
            }
        elif current and stripped.startswith("type "):
            current["type"] = stripped.split(None, 1)[1]
    if current:
        interfaces.append(current)

    states = get_nmcli_device_states()
    for interface in interfaces:
        interface["state"] = states.get(interface["name"], "not managed")
        interface["driver"] = get_driver(interface["name"])
        interface["monitor"] = (
            "yes" if supports_monitor_mode(interface["phy"]) else "not reported"
        )
    return interfaces


def get_driver(interface: str) -> str:
    if shutil.which("ethtool") is None:
        return "unknown"
    result = run_command(["ethtool", "-i", interface])
    if result.returncode != 0:
        return "unknown"
    for line in result.stdout.splitlines():
        if line.lower().startswith("driver:"):
            return line.split(":", 1)[1].strip() or "unknown"
    return "unknown"


def supports_monitor_mode(phy: str) -> bool:
    if phy == "unknown" or shutil.which("iw") is None:
        return False
    result = run_command(["iw", "phy", phy, "info"])
    if result.returncode != 0:
        return False
    in_modes = False
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if stripped.startswith("Supported interface modes:"):
            in_modes = True
            continue
        if in_modes and stripped.startswith("*"):
            if stripped[1:].strip() == "monitor":
                return True
        elif in_modes and stripped and not line.startswith("\t"):
            break
    return False


def print_interfaces(interfaces: list[dict[str, str]]) -> None:
    print("\nWirelessRecon — wireless interfaces")
    print("-" * 88)
    print(f"{'INTERFACE':<14} {'DRIVER':<18} {'STATE':<20} {'TYPE':<14} MONITOR")
    print("-" * 88)
    if not interfaces:
        print("No wireless interfaces were detected.")
    for item in interfaces:
        print(
            f"{item['name']:<14} {item['driver']:<18} {item['state']:<20} "
            f"{item['type']:<14} {item['monitor']}"
        )
    print("-" * 88)


def validate_interface(interface: str) -> None:
    available = {item["name"] for item in get_wireless_interfaces()}
    if interface not in available:
        found = ", ".join(sorted(available)) or "none"
        raise WirelessReconError(
            f"Wireless interface '{interface}' was not found. Detected interfaces: {found}. "
            "Run --list-interfaces to inspect adapters."
        )


def get_interface_ipv4(interface: str) -> str:
    if shutil.which("ip") is None:
        raise WirelessReconError("'ip' was not found. Install the iproute2 package.")
    result = run_command(["ip", "-4", "-o", "addr", "show", "dev", interface, "scope", "global"])
    if result.returncode != 0:
        raise WirelessReconError(result.stderr.strip() or f"Unable to inspect IPv4 address for {interface}.")
    for line in result.stdout.splitlines():
        match = re.search(r"\binet\s+(\d{1,3}(?:\.\d{1,3}){3})/\d+\b", line)
        if match:
            return match.group(1)
    raise WirelessReconError(
        f"{interface} has no global IPv4 address. Connect your own lab device/network "
        "before starting this host-only capture."
    )


def capture_host_traffic(interface: str, duration: int, output_path: Path) -> Path:
    """Capture only packets addressed to/from this host's assigned IPv4 address."""
    if shutil.which("dumpcap") is None:
        raise WirelessReconError(
            "dumpcap was not found. Install Wireshark tools with: sudo apt install wireshark-common"
        )
    if duration < 1 or duration > MAX_CAPTURE_SECONDS:
        raise WirelessReconError(f"Capture duration must be between 1 and {MAX_CAPTURE_SECONDS} seconds.")

    host_ip = get_interface_ipv4(interface)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        raise WirelessReconError(f"Refusing to overwrite existing capture: {output_path}")

    started = datetime.now(timezone.utc)
    print(f"Starting {duration}-second host-only capture on {interface} ({host_ip}).")
    print("Capture filter: packets to or from this Kali host's IPv4 address.")
    print("Only capture traffic on networks and devices you are authorized to assess.")

    command = [
        "dumpcap", "-q", "-i", interface,
        "-f", f"host {host_ip}",
        "-a", f"duration:{duration}",
        "-w", str(output_path),
    ]
    result = run_command(command, timeout=duration + 30)
    ended = datetime.now(timezone.utc)
    if result.returncode != 0:
        if output_path.exists() and output_path.stat().st_size == 0:
            output_path.unlink()
        message = result.stderr.strip() or result.stdout.strip() or "dumpcap failed."
        raise WirelessReconError(message)

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise WirelessReconError("Capture ended without producing a non-empty PCAPNG file.")

    metadata = {
        "tool": "WirelessRecon",
        "version": VERSION,
        "capture_format": "pcapng",
        "interface": interface,
        "host_ipv4": host_ip,
        "capture_filter": f"host {host_ip}",
        "scope": "traffic to/from this host only",
        "started_at": started.isoformat(),
        "ended_at": ended.isoformat(),
        "duration_seconds_requested": duration,
        "file": str(output_path),
        "file_size_bytes": output_path.stat().st_size,
    }
    metadata_path = output_path.with_suffix(output_path.suffix + ".json")
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    print(f"PCAPNG capture saved: {output_path}")
    print(f"Capture metadata saved: {metadata_path}")
    print(f"File size: {output_path.stat().st_size} bytes")
    return output_path


def run_nmcli(rescan: bool = True, interface: str | None = None) -> list[str]:
    if shutil.which("nmcli") is None:
        raise WirelessReconError(
            "nmcli was not found. Install NetworkManager (for example: sudo apt install network-manager)."
        )
    command = [
        "nmcli", "--terse", "--escape", "yes",
        "--fields", ",".join(FIELDS), "device", "wifi", "list",
    ]
    if interface:
        command.extend(["ifname", interface])
    if rescan:
        command.extend(["--rescan", "yes"])
    result = run_command(command, timeout=45)
    if result.returncode != 0:
        raise WirelessReconError(
            result.stderr.strip() or "NetworkManager could not scan for Wi-Fi networks."
        )
    return [line for line in result.stdout.splitlines() if line.strip()]


def parse_networks(lines: Iterable[str]) -> list[dict[str, str | int | None]]:
    networks: list[dict[str, str | int | None]] = []
    for line in lines:
        values = split_nmcli_fields(line)
        if len(values) != len(FIELDS):
            continue
        ssid, bssid, channel, frequency, rate, signal, security = values
        try:
            signal_value: int | None = int(signal) if signal else None
        except ValueError:
            signal_value = None
        networks.append({
            "ssid": ssid or "<hidden>",
            "bssid": bssid or None,
            "channel": channel or None,
            "frequency": frequency or None,
            "rate": rate or None,
            "signal_percent": signal_value,
            "security": security or "Open / not reported",
        })
    return networks


def print_networks(networks: list[dict[str, str | int | None]]) -> None:
    print(f"\nWirelessRecon — networks discovered: {len(networks)}")
    print("-" * 104)
    print(f"{'SSID':<26} {'BSSID':<19} {'CH':<5} {'FREQ':<10} {'SIGNAL':<9} SECURITY")
    print("-" * 104)
    for network in networks:
        ssid = str(network["ssid"]).replace("\n", " ")[:25]
        bssid = str(network["bssid"] or "-")
        channel = str(network["channel"] or "-")
        frequency = str(network["frequency"] or "-")
        signal = f"{network['signal_percent']}%" if network["signal_percent"] is not None else "-"
        security = str(network["security"] or "-")
        print(f"{ssid:<26} {bssid:<19} {channel:<5} {frequency:<10} {signal:<9} {security}")
    print("-" * 104)


def save_report(networks: list[dict[str, str | int | None]], output_path: Path,
                interface: str | None = None) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "tool": "WirelessRecon",
        "version": VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "interface": interface,
        "network_count": len(networks),
        "networks": networks,
    }
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Discover nearby Wi-Fi networks and capture your own host's traffic."
    )
    parser.add_argument(
        "--list-interfaces", action="store_true",
        help="List detected wireless interfaces, drivers, state, and reported monitor-mode support.",
    )
    parser.add_argument(
        "--interface", metavar="IFACE",
        help="Select a wireless interface (for example: wlan0).",
    )
    parser.add_argument(
        "--capture", action="store_true",
        help="Capture traffic to/from this host's IPv4 address into a PCAPNG file.",
    )
    parser.add_argument(
        "--duration", type=int, default=30,
        help=f"Capture duration in seconds (1-{MAX_CAPTURE_SECONDS}; default: 30).",
    )
    parser.add_argument(
        "--capture-output", type=Path,
        help="PCAPNG output path (default: captures/capture_TIMESTAMP.pcapng).",
    )
    parser.add_argument(
        "--no-rescan", action="store_true",
        help="Use NetworkManager's current scan results without requesting a new scan.",
    )
    parser.add_argument("--output", type=Path, help="JSON report path.")
    parser.add_argument(
        "--no-save", action="store_true",
        help="Print discovery results without saving a JSON report.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.list_interfaces:
            print_interfaces(get_wireless_interfaces())
            return 0

        if args.capture:
            if not args.interface:
                raise WirelessReconError("--capture requires --interface so the capture device is explicit.")
            validate_interface(args.interface)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output = args.capture_output or Path("captures") / f"capture_{timestamp}.pcapng"
            capture_host_traffic(args.interface, args.duration, output)
            return 0

        if args.interface:
            validate_interface(args.interface)
        networks = parse_networks(
            run_nmcli(rescan=not args.no_rescan, interface=args.interface)
        )
        if args.interface:
            print(f"Wireless interface: {args.interface}")
        print_networks(networks)
        if not args.no_save:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output = args.output or Path("reports") / f"scan_{timestamp}.json"
            print(f"JSON report saved: {save_report(networks, output, args.interface)}")
        return 0
    except WirelessReconError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"[ERROR] File operation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
