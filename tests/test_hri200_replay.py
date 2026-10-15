# Copyright 2026 IU0NDT
# SPDX-License-Identifier: Apache-2.0
"""Synthetic PCAP replay integration tests; no physical I/O."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from hri200_replay import replay
from test_hri200_pcap_decode import pcap, usb_packet


class ReplayTests(unittest.TestCase):
    def test_offline_replay_and_privacy(self):
        private_reply = b"\x01R0" + b"12345,56789,TEST9999,12345678901234".hex().encode() + b"\x04"
        packets = [
            usb_packet(1, 0x01, 3, b"\x01M10\x04", address=9),
            usb_packet(2, 0x82, 3, b"\x01M10\x04", address=9),
            usb_packet(3, 0x01, 3, b"\x01P010000\x04", address=9),
            usb_packet(4, 0x82, 3, b"\x01B0 0    0000000\x04", address=9),
            usb_packet(5, 0x82, 3, private_reply, address=9),
            usb_packet(6, 0x01, 3, b"\x01D1V0000\x04", address=9),
            usb_packet(7, 0x01, 3, b"\x01P010000\x04", address=10),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "synthetic.pcap"
            path.write_bytes(pcap(packets))
            result = replay(path, 9)
        self.assertEqual(result["rx_frames"], 3)
        self.assertEqual(result["tx_frames"], 3)
        self.assertEqual(result["capture"]["pcap_records"], 7)
        self.assertEqual(result["capture"]["selected_bulk_data_records"], 6)
        self.assertEqual(result["observed_frames"]["TX:D1V0000"], 1)
        self.assertEqual(result["observed_frames"]["RX:R0_REDACTED"], 1)
        self.assertEqual(result["poll_response_fifo"]["pairs"], 1)
        self.assertNotIn("TEST9999", str(result))
        self.assertNotIn("12345", str(result))

    def test_wrong_usb_address(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "synthetic.pcap"
            path.write_bytes(pcap([usb_packet(1, 0x01, 3, b"\x01M10\x04", address=4)]))
            with self.assertRaisesRegex(ValueError, "No recorded bulk"):
                replay(path, 5)


if __name__ == "__main__":
    unittest.main()
