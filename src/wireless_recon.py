#!/usr/bin/env python3
"""WirelessRecon: Linux Wi-Fi discovery and defensive inventory."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

FIELDS = ("SSID", "BSSID", "CHAN", "FREQ", "RATE", "SIGNAL", "SECURITY")


class WirelessReconError(RuntimeError):
    """Raised when wireless discovery cannot be completed."""


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


def run_nmcli(rescan: bool = True) -> list[str]:
    if shutil.which("nmcli") is None:
        raise WirelessReconError(
            "nmcli was not found. Install NetworkManager "
            "(for example: sudo apt install network-manager)."
        )

    command = [
        "nmcli", "--terse", "--escape", "yes",
        "--fields", ",".join(FIELDS), "device", "wifi", "list",
    ]
    if rescan:
        command.extend(["--rescan", "yes"])

    try:
        result = subprocess.run(
            command, check=False, capture_output=True, text=True, timeout=45
        )
    except subprocess.TimeoutExpired as exc:
        raise WirelessReconError("The Wi-Fi scan timed out.") from exc
    except OSError as exc:
        raise WirelessReconError(f"Unable to run nmcli: {exc}") from exc

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


def save_report(networks: list[dict[str, str | int | None]], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "tool": "WirelessRecon",
        "version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "network_count": len(networks),
        "networks": networks,
    }
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Discover nearby Wi-Fi networks using Linux NetworkManager."
    )
    parser.add_argument(
        "--no-rescan", action="store_true",
        help="Use NetworkManager's current scan results without requesting a new scan.",
    )
    parser.add_argument(
        "--output", type=Path,
        help="JSON report path (default: reports/scan_TIMESTAMP.json).",
    )
    parser.add_argument(
        "--no-save", action="store_true",
        help="Print results without saving a JSON report.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        networks = parse_networks(run_nmcli(rescan=not args.no_rescan))
        print_networks(networks)
        if not args.no_save:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output = args.output or Path("reports") / f"scan_{timestamp}.json"
            print(f"JSON report saved: {save_report(networks, output)}")
        return 0
    except WirelessReconError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"[ERROR] File operation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
