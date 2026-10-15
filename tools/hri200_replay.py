#!/usr/bin/env python3
# Copyright 2026 IU0NDT
# SPDX-License-Identifier: Apache-2.0
"""Replay an existing private USBPcap capture through the new passive HRI-200 core.

This program is OFFLINE ONLY. It never opens serial/USB/audio devices and it
never exports the raw capture, R0 identities or unknown frame contents.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core"))

from hri200_protocol import PassiveSession
from hri200_pcap_decode import read_pcap, usb_record


def replay(capture: Path, device: int) -> dict:
    session = PassiveSession()
    pcap_records = 0
    selected_bulk_records = 0
    for timestamp, packet in read_pcap(capture):
        pcap_records += 1
        record = usb_record(packet)
        if record is None:
            continue
        _irp, address, endpoint, kind, _stage, data = record
        if address != device or kind != 3 or not data:
            continue
        selected_bulk_records += 1
        direction = "RX" if endpoint & 0x80 else "TX"
        session.observe(direction, data, timestamp)

    if selected_bulk_records == 0:
        raise ValueError(
            "No recorded bulk payloads for this USB address; "
            "check the private PCAP and capture-specific --device argument"
        )
    summary = session.report()
    summary["capture"] = {
        "pcap_records": pcap_records,
        "selected_bulk_data_records": selected_bulk_records,
        "usb_address_selection": "explicit_capture_argument",
        "source": "local_offline_USBPcap",
    }
    return summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path, help="Local, privately stored classic USBPcap file")
    parser.add_argument(
        "--device", type=int, required=True,
        help="USB device address in THIS recording; not a stable device identifier",
    )
    args = parser.parse_args(argv)
    if not 0 <= args.device <= 65535:
        parser.error("--device must be between 0 and 65535")
    try:
        summary = replay(args.capture, args.device)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Offline replay failed: {exc}\n")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
