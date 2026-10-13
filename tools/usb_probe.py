#!/usr/bin/env python3
# Copyright 2026 IU0NDT
# SPDX-License-Identifier: Apache-2.0
# Source: https://github.com/pof66/netithub-wiresx-linux

"""Read-only Linux sysfs discovery for YAESU HRI-200 USB interfaces.

No USB device nodes are opened; serial, audio and HID ports are never touched.
This script may safely operate on fake sysfs trees for regression testing.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

DEFAULT_SYSFS = Path('/sys/bus/usb/devices')
YAESU_VENDOR_ID = '26aa'
HRI_200_PRODUCT_IDS = frozenset(('0002', '0003'))


def read_attr(directory: Path, name: str) -> str | None:
    try:
        return (directory / name).read_text(encoding='ascii').strip()
    except (OSError, UnicodeError):
        return None


def probe(root: Path, vendor: str = YAESU_VENDOR_ID,
          product_ids: frozenset[str] | None = HRI_200_PRODUCT_IDS) -> list[dict[str, Any]]:
    """Return USB descriptors from sysfs without opening an actual USB device."""
    results: list[dict[str, Any]] = []
    try:
        entries = sorted(root.iterdir(), key=lambda item: item.name)
    except OSError:
        return results

    for device in entries:
        if not device.is_dir() or ':' in device.name:
            continue
        vid = read_attr(device, 'idVendor')
        pid = read_attr(device, 'idProduct')
        if not vid or not pid or vid.lower() != vendor.lower():
            continue
        if product_ids is not None and pid.lower() not in product_ids:
            continue

        interfaces: list[dict[str, str | None]] = []
        for interface in entries:
            if not interface.name.startswith(device.name + ':') or not interface.is_dir():
                continue
            driver_link = interface / 'driver'
            driver = driver_link.resolve().name if driver_link.is_symlink() else None
            interfaces.append({
                'interface': interface.name.split(':', 1)[1],
                'class': read_attr(interface, 'bInterfaceClass'),
                'subclass': read_attr(interface, 'bInterfaceSubClass'),
                'protocol': read_attr(interface, 'bInterfaceProtocol'),
                'driver': driver,
            })

        results.append({
            'usb_path': device.name,
            'vendor_id': vid.lower(),
            'product_id': pid.lower(),
            'manufacturer': read_attr(device, 'manufacturer'),
            'product': read_attr(device, 'product'),
            'interfaces': interfaces,
        })
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sysfs-root', type=Path, default=DEFAULT_SYSFS,
                        help='Root of Linux USB sysfs or an offline test fixture')
    parser.add_argument('--vendor-id', default=YAESU_VENDOR_ID,
                        help='Four hexadecimal digits (default: 26aa)')
    parser.add_argument('--all-products', action='store_true',
                        help='Show every USB product with the selected vendor ID')
    args = parser.parse_args()
    vendor = args.vendor_id.strip().lower()
    if len(vendor) != 4 or any(ch not in '0123456789abcdef' for ch in vendor):
        parser.error('--vendor-id must be exactly four hexadecimal digits')
    matches = probe(args.sysfs_root, vendor,
                    None if args.all_products else HRI_200_PRODUCT_IDS)
    print(json.dumps({'devices': matches, 'count': len(matches)}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
