#!/usr/bin/env python3
# Copyright 2026 IU0NDT
# SPDX-License-Identifier: Apache-2.0
# Source: https://github.com/pof66/netithub-wiresx-linux

"""Discover HRI-200 USB serial and ALSA endpoints via Linux sysfs (read-only).

This tool does NOT open /dev/tty*, /dev/snd/* or /dev/hidraw*; it never sends
commands, captures audio, adjusts controls or contacts network services.

A HRI-200 appears as *two* USB devices (26aa:0002 serial, 26aa:0003 audio/HID).
On systems with multiple units, enumeration alone does not prove which two
devices belong to the same physical HRI-200; an operator must select explicitly.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

VENDOR = "26aa"
SERIAL_PID = "0002"
AUDIO_PID = "0003"


def _attribute(path: Path, name: str) -> str | None:
    try:
        return (path / name).read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        return None


def _usb_ancestor(path: Path, vendor: str, product: str) -> Path | None:
    """Follow sysfs parents, accepting only exact matching USB vendor/product."""
    try:
        parent = path.resolve(strict=True)
    except (OSError, RuntimeError):
        return None
    for node in (parent, *parent.parents):
        vid = _attribute(node, "idVendor")
        pid = _attribute(node, "idProduct")
        if vid is not None and pid is not None:
            # A nonmatching USB device is a boundary: never adopt a USB hub ID.
            if vid.lower() == vendor.lower() and pid.lower() == product.lower():
                return node
            return None
    return None


def _entries(path: Path) -> list[Path]:
    try:
        return sorted(path.iterdir(), key=lambda item: item.name)
    except OSError:
        return []


def discover(sys_class: Path = Path("/sys/class"),
             vendor: str = VENDOR,
             serial_pid: str = SERIAL_PID,
             audio_pid: str = AUDIO_PID) -> dict[str, Any]:
    """Return detected endpoints without opening their corresponding /dev nodes."""
    serial: list[dict[str, str]] = []
    for tty in _entries(sys_class / "tty"):
        if not tty.name.startswith("ttyACM"):
            continue
        device = tty / "device"
        usb = _usb_ancestor(device, vendor, serial_pid)
        if usb is None:
            continue
        serial.append({
            "device": "/dev/" + tty.name,
            "usb_port": usb.name,
            "vid": vendor.lower(),
            "pid": serial_pid.lower(),
            "usb_product": _attribute(usb, "product") or "",
        })

    audio: list[dict[str, Any]] = []
    sound = sys_class / "sound"
    sound_entries = _entries(sound)
    for card in sound_entries:
        if not (card.name.startswith("card") and card.name[4:].isdigit()):
            continue
        usb = _usb_ancestor(card / "device", vendor, audio_pid)
        if usb is None:
            continue
        number = card.name[4:]
        pcms = {"capture": [], "playback": []}
        for item in sound_entries:
            # PCM enumeration only. Never open these paths.
            if item.name.startswith("pcmC" + number + "D") and item.name[-1:] in ("c", "p"):
                direction = "capture" if item.name.endswith("c") else "playback"
                pcms[direction].append("/dev/snd/" + item.name)
        audio.append({
            "card": card.name,
            "alsa_id": _attribute(card, "id"),
            "usb_port": usb.name,
            "vid": vendor.lower(),
            "pid": audio_pid.lower(),
            "usb_product": _attribute(usb, "product") or "",
            "pcm": pcms,
        })

    # Never silently associate endpoints when more than one candidate exists.
    status = (
        "missing_endpoint" if not serial or not audio else
        "operator_selection_required" if len(serial) != 1 or len(audio) != 1 else
        "one_serial_one_audio_candidate"
    )
    return {
        "schema": "hri200-linux-discovery-v1",
        "serial": serial,
        "audio": audio,
        "status": status,
        "note": "Candidate enumeration only; no hardware I/O or proven physical USB pairing.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sys-class", type=Path, default=Path("/sys/class"),
                        help="Linux /sys/class (or isolated mock for tests)")
    args = parser.parse_args()
    print(json.dumps(discover(args.sys_class), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
