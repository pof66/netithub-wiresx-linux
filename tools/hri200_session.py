#!/usr/bin/env python3
# Copyright 2026 IU0NDT
# SPDX-License-Identifier: Apache-2.0
"""NET.IT.HUB HRI-200 Linux serial session proof (not WIRES-X service login).

Default: USB discovery ONLY, no serial open or USB writes.
Active: --run-once --rf-isolated, three previously observed exchanges, no loop.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core"))
sys.path.insert(0, str(ROOT / "hardware"))
sys.path.insert(0, str(ROOT / "tools"))

from hri200_discovery import discover
from hri200_cdc import LinuxCDC, choose_serial_endpoint, run_verified_sequence


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", help="Choose a discovered HRI-200 tty (needed when ambiguous)")
    parser.add_argument("--run-once", action="store_true",
                        help="Explicitly request three observed HRI-200 serial exchanges")
    parser.add_argument("--rf-isolated", action="store_true",
                        help="Confirm radios/PTT are physically disconnected and RF is disabled")
    args = parser.parse_args(argv)

    if args.rf_isolated and not args.run_once:
        parser.error("--rf-isolated alone performs no test; add --run-once if intended")
    if args.run_once and not args.rf_isolated:
        parser.error("Active serial I/O requires both --run-once and --rf-isolated")

    state = discover()
    serial = state["serial"]
    print(json.dumps({
        "schema": "netithub-hri200-linux-session-v1",
        "mode": "one_time_serial_test" if args.run_once else "discovery_only",
        "serial_candidates": serial,
        "audio_candidates": len(state["audio"]),
        "hid_candidates": len(state["hid"]),
        "rf_tx": "not_enabled_by_this_software",
        "yaesu_network": "not_implemented",
    }, indent=2, ensure_ascii=False), flush=True)

    if not args.run_once:
        print("Discovery complete; no serial port opened and no bytes transmitted.")
        return 0

    try:
        device = choose_serial_endpoint(serial, selected=args.port)
        print("Opening the verified CDC device; no unknown commands or polling loops.",
              flush=True)
        print("NOTE: opening Linux CDC ACM can implicitly affect DTR/RTS.", flush=True)
        with LinuxCDC(device) as connection:
            results = run_verified_sequence(connection.transact)
        print(json.dumps({
            "schema": "netithub-hri200-linux-session-result-v1",
            "hardware_serial": "three_single_shot_exchanges_passed",
            "steps": [item.redacted() for item in results],
            "rf_tx": "not_enabled_by_this_software",
            "yaesu_worldwide_connection": "not_implemented",
            "brandmeister_bridge": "not_implemented",
        }, indent=2, ensure_ascii=False))
        return 0
    except (OSError, RuntimeError, ValueError, TimeoutError) as exc:
        # Show only exception type: kernel messages can contain local device details.
        print("Session aborted safely: " + type(exc).__name__
              + ". No further serial command sent.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
