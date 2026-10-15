#!/usr/bin/env python3
# Copyright 2026 IU0NDT
# SPDX-License-Identifier: Apache-2.0
# Source: https://github.com/pof66/netithub-wiresx-linux
"""Offline, read-only and redacted USBPcap HRI-200 CDC serial-frame summary.

No serial devices, audio devices, network endpoints or radio hardware are opened.
The recorded USB address is selected by the user, never hardcoded.
Raw data and unknown command payloads are never printed.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
import statistics
import struct
from pathlib import Path

PCAP_MAGIC = {
    b"\xd4\xc3\xb2\xa1": ("<", 1_000_000),
    b"\xa1\xb2\xc3\xd4": (">", 1_000_000),
    b"\x4d\x3c\xb2\xa1": ("<", 1_000_000_000),
    b"\xa1\xb2\x3c\x4d": (">", 1_000_000_000),
}
USBPCAP_LINKTYPE = 249
FRAMES = {
    b"M10": "M10",
    b"R6423": "R6423",
    b"P010000": "P010000",
    b"B0 0    0000000": "B0_status_sample",
    b"D1V0000": "D1V0000",
}
LINE_CODING = {
    0: "1",
    1: "1.5",
    2: "2",
}
MAX_PACKET = 16 * 1024 * 1024
MAX_FRAME = 4096


def read_pcap(path):
    """Yield (timestamp_seconds, USBPcap record), validating classic PCAP."""
    with Path(path).open("rb") as handle:
        gh = handle.read(24)
        if len(gh) != 24 or gh[:4] not in PCAP_MAGIC:
            raise ValueError("Not a supported classic PCAP file")
        endian, clock = PCAP_MAGIC[gh[:4]]
        _, _, _, _, _, linktype = struct.unpack_from(endian + "HHIIII", gh, 4)
        if linktype != USBPCAP_LINKTYPE:
            raise ValueError(f"Expected USBPcap LinkType 249, got {linktype}")
        while True:
            header = handle.read(16)
            if not header:
                return
            if len(header) != 16:
                raise ValueError("Truncated PCAP record header")
            sec, fraction, included, original = struct.unpack(endian + "IIII", header)
            if included > MAX_PACKET or included > original:
                raise ValueError("Invalid PCAP record length")
            packet = handle.read(included)
            if len(packet) != included:
                raise ValueError("Truncated PCAP packet")
            yield sec + fraction / clock, packet


def usb_record(packet):
    """Return selected USBPcap fields, or None for too-short records."""
    if len(packet) < 27:
        return None
    hdr_len, irp, _status, _function, _info, _bus, device, endpoint, kind, size = (
        struct.unpack_from("<HQIHBHHBBI", packet)
    )
    if hdr_len < 27 or hdr_len > len(packet):
        return None
    available = len(packet) - hdr_len
    if size > available:
        # Snaplen truncation / missing bytes: never parse partial content as valid.
        return None
    stage = packet[27] if kind == 2 and hdr_len >= 28 else None
    return irp, device, endpoint, kind, stage, packet[hdr_len:hdr_len + size]


def classify_frame(body):
    if body.startswith(b"R0"):
        encoded = body[2:]
        try:
            if not encoded or len(encoded) % 2:
                raise ValueError("odd-length hex")
            decoded = bytes.fromhex(encoded.decode("ascii"))
            fields = decoded.split(b",")
            types = []
            for field in fields:
                if field.isdigit():
                    types.append("numeric")
                elif field.isalnum() and field.isascii():
                    types.append("alphanumeric")
                else:
                    types.append("other")
            return "R0_REDACTED", (len(decoded), tuple(len(f) for f in fields), tuple(types))
        except (UnicodeError, ValueError):
            return "R0_REDACTED_UNPARSEABLE", None
    return FRAMES.get(body, "UNKNOWN_REDACTED"), None


def decode(path, device):
    """Pure offline summary; no full payload strings are retained or returned."""
    stats = Counter()
    patterns = Counter()
    control = Counter()
    lines = Counter()
    r0_shapes = Counter()
    buffers = defaultdict(bytearray)
    pending_control = {}
    poll_requests = deque()
    delays = []

    for timestamp, packet in read_pcap(path):
        stats["pcap_records"] += 1
        rec = usb_record(packet)
        if rec is None:
            stats["unparsed_usb_records"] += 1
            continue
        irp, dev, endpoint, kind, stage, payload = rec
        if dev != device:
            continue
        stats["selected_usb_records"] += 1

        if kind == 2:
            if stage == 0 and len(payload) >= 8:
                req_type, req, value, index, length = struct.unpack_from("<BBHHH", payload)
                label = {
                    (0xA1, 0x21): "GET_LINE_CODING",
                    (0x21, 0x20): "SET_LINE_CODING",
                    (0x21, 0x22): "SET_CONTROL_LINE_STATE",
                }.get((req_type, req), "OTHER_CONTROL")
                control[label] += 1
                pending_control[irp] = label
                if label == "SET_CONTROL_LINE_STATE":
                    control["DTR_RTS_BOTH" if value == 3 else "OTHER_CONTROL_LINES"] += 1
                if label == "SET_LINE_CODING" and len(payload) >= 15 and length == 7:
                    lines[tuple(payload[8:15])] += 1
            elif stage == 3:
                label = pending_control.pop(irp, None)
                if label == "GET_LINE_CODING" and len(payload) == 7:
                    lines[tuple(payload)] += 1
            continue
        if kind != 3 or not payload:
            continue

        direction = "RX" if endpoint & 0x80 else "TX"
        stats["bulk_data_records"] += 1
        buf = buffers[(endpoint, direction)]

        for byte in payload:
            if not buf:
                if byte == 0x01:
                    buf.append(byte)
                continue
            if byte == 0x01:
                stats["resync"] += 1
                buf.clear()
                buf.append(byte)
            elif byte == 0x04:
                label, shape = classify_frame(bytes(buf[1:]))
                patterns[(direction, label)] += 1
                stats["complete_frames"] += 1
                if shape:
                    r0_shapes[shape] += 1
                if direction == "TX" and label == "P010000":
                    poll_requests.append(timestamp)
                elif direction == "RX" and label == "B0_status_sample" and poll_requests:
                    delays.append((timestamp - poll_requests.popleft()) * 1000)
                buf.clear()
            elif len(buf) >= MAX_FRAME:
                stats["oversized_frame"] += 1
                buf.clear()
            else:
                buf.append(byte)

    stats["pending_poll_requests"] = len(poll_requests)
    stats["incomplete_frame_buffers"] = sum(bool(b) for b in buffers.values())
    return stats, patterns, control, lines, r0_shapes, delays


def summary(path, device):
    stats, patterns, control, lines, shapes, delays = decode(path, device)
    print("NET.IT.HUB HRI-200 offline USBPcap decoder — REDACTED")
    print(f"Recorded USB device address: {device} (capture-specific, not a default)")
    for name in ("pcap_records", "selected_usb_records", "bulk_data_records",
                 "complete_frames", "unparsed_usb_records", "resync",
                 "oversized_frame", "incomplete_frame_buffers"):
        print(f"{name}: {stats[name]}")
    print("Frames (contents of unknown frames and R0 fields are suppressed):")
    for (direction, label), count in sorted(patterns.items()):
        print(f"  {direction} {label}: {count}")
    print("USB CDC setup operations:")
    for label, count in sorted(control.items()):
        print(f"  {label}: {count}")
    for coded, count in sorted(lines.items()):
        baud = int.from_bytes(bytes(coded[:4]), "little")
        stop = LINE_CODING.get(coded[4], "unknown")
        print(f"  line coding: {baud} baud / {coded[6]} data bits / parity code {coded[5]} / {stop} stop bit(s): {count}")
    for (byte_count, lengths, types), count in sorted(shapes.items()):
        print(f"R0 redacted decoded shape: {byte_count} bytes; field lengths={lengths}; types={types}; count={count}")
    if delays:
        print(f"P->B FIFO pairing (not protocol timeout): count={len(delays)}, "
              f"min={min(delays):.3f} ms, mean={statistics.mean(delays):.3f} ms, "
              f"max={max(delays):.3f} ms, unmatched_P={stats['pending_poll_requests']}")
    print("Offline inspection only. No proof of PTT, audio or native WIRES-X networking.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pcap", type=Path, help="Private local USBPcap .pcap file")
    parser.add_argument("--device", type=int, required=True,
                        help="USB device ADDRESS as recorded in this PCAP")
    args = parser.parse_args()
    if not 0 <= args.device <= 65535:
        parser.error("--device must be between 0 and 65535")
    try:
        summary(args.pcap, args.device)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Cannot decode capture: {exc}\n")


if __name__ == "__main__":
    main()
