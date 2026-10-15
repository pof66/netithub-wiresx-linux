# Copyright 2026 IU0NDT
# SPDX-License-Identifier: Apache-2.0
# Source: https://github.com/pof66/netithub-wiresx-linux
"""Synthetic, offline tests: no real USB/serial/audio/radio access."""
import io
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import hri200_pcap_decode as decoder


def usb_packet(irp, ep, kind, payload, stage=None, address=7):
    header_length = 28 if kind == 2 else 27
    header = struct.pack(
        "<HQIHBHHBBI", header_length, irp, 0, 0, 0,
        1, address, ep, kind, len(payload),
    )
    return header + (bytes([stage]) if stage is not None else b"") + payload


def pcap(records, linktype=249):
    out = io.BytesIO()
    out.write(struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, linktype))
    for index, payload in enumerate(records):
        out.write(struct.pack("<IIII", 10, 1000 + index * 1000,
                              len(payload), len(payload)))
        out.write(payload)
    return out.getvalue()


class OfflinePcapTests(unittest.TestCase):
    def run_capture(self, contents, device=7):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "private-synthetic.pcap"
            target.write_bytes(contents)
            return decoder.decode(target, device)

    def test_frame_reassembly_and_redaction(self):
        frame = b"\x01P010000\x04"
        response = b"\x01B0 0    0000000\x04"
        private = b"\x01R0" + b"00000,00000,ABCD1234,20261015112233".hex().encode("ascii") + b"\x04"
        records = [
            usb_packet(1, 0x01, 3, frame[:4]),
            usb_packet(2, 0x01, 3, frame[4:]),
            usb_packet(3, 0x82, 3, response),
            usb_packet(4, 0x82, 3, private),
            usb_packet(5, 0x01, 3, b"\x01PRIVATE_SENSITIVE_CONTENT\x04"),
            usb_packet(6, 0x01, 3, frame, address=15),
        ]
        stats, names, control, lines, shapes, delays = self.run_capture(pcap(records))
        self.assertEqual(stats["complete_frames"], 4)
        self.assertEqual(names[("TX", "P010000")], 1)
        self.assertEqual(names[("RX", "B0_status_sample")], 1)
        self.assertEqual(names[("RX", "R0_REDACTED")], 1)
        self.assertEqual(names[("TX", "UNKNOWN_REDACTED")], 1)
        self.assertEqual(len(delays), 1)
        self.assertEqual(list(shapes.keys())[0][1], (5, 5, 8, 14))
        self.assertNotIn("ABCD1234", str(names) + str(shapes))
        self.assertNotIn("PRIVATE_SENSITIVE_CONTENT", str(names) + str(shapes))

    def test_cdc_setup_get_set_and_control_line(self):
        line = bytes.fromhex("00960000000008")
        get_setup = bytes.fromhex("A121000000000700")
        set_setup = bytes.fromhex("2120000000000700") + line
        dtr_rts_setup = bytes.fromhex("2122030000000000")
        capture = pcap([
            usb_packet(10, 0x80, 2, get_setup, stage=0),
            usb_packet(10, 0x80, 2, line, stage=3),
            usb_packet(11, 0x00, 2, set_setup, stage=0),
            usb_packet(11, 0x00, 2, b"", stage=3),
            usb_packet(12, 0x00, 2, dtr_rts_setup, stage=0),
            usb_packet(12, 0x00, 2, b"", stage=3),
        ])
        _, _, control, lines, _, _ = self.run_capture(capture)
        self.assertEqual(control["GET_LINE_CODING"], 1)
        self.assertEqual(control["SET_LINE_CODING"], 1)
        self.assertEqual(control["SET_CONTROL_LINE_STATE"], 1)
        self.assertEqual(control["DTR_RTS_BOTH"], 1)
        self.assertEqual(lines[tuple(line)], 2)

    def test_reject_wrong_linktype(self):
        with self.assertRaisesRegex(ValueError, "LinkType"):
            self.run_capture(pcap([], linktype=1))

    def test_reject_truncated_record(self):
        record = usb_packet(1, 0x01, 3, b"\x01M10\x04")
        with self.assertRaisesRegex(ValueError, "Truncated PCAP packet"):
            self.run_capture(pcap([record])[:-2])


if __name__ == "__main__":
    unittest.main()
