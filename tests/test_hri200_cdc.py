# Copyright 2026 IU0NDT
# SPDX-License-Identifier: Apache-2.0
"""Offline/mocked tests for opt-in HRI-200 hardware transport.

PTY loopback test simulates an isolated serial device: no physical USB opened.
"""
from pathlib import Path
import os
import sys
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "core"))
sys.path.insert(0, str(ROOT / "hardware"))
sys.path.insert(0, str(ROOT / "tools"))
from hri200_protocol import FrameEvent, FrameStream
from hri200_cdc import LinuxCDC, choose_serial_endpoint, run_verified_sequence


CANDIDATES = [
    {"device": "/dev/ttyACM7", "vid": "26aa", "pid": "0002"},
    {"device": "/dev/ttyUSB42", "vid": "other", "pid": "0002"},
]


class SafeTransportTests(unittest.TestCase):
    def test_discovery_selection_and_no_fixed_tty(self):
        self.assertEqual(choose_serial_endpoint(CANDIDATES), "/dev/ttyACM7")
        self.assertEqual(choose_serial_endpoint(CANDIDATES, "/dev/ttyACM7"), "/dev/ttyACM7")
        with self.assertRaisesRegex(ValueError, "not found"):
            choose_serial_endpoint(CANDIDATES, "/dev/ttyUSB42")
        with self.assertRaisesRegex(ValueError, "Multiple"):
            choose_serial_endpoint(CANDIDATES + [
                {"device": "/dev/ttyACM8", "vid": "26AA", "pid": "0002"}
            ])
        with self.assertRaisesRegex(ValueError, "No verified"):
            choose_serial_endpoint([])

    def test_strict_sequence_offline(self):
        requests = []
        labels = ("M10", "R0_REDACTED", "B0_OBSERVED_RESPONSE")
        def transaction(request, expected, timeout):
            index = len(requests)
            requests.append(request)
            self.assertEqual(expected, labels[index])
            self.assertEqual(timeout, 2.0)
            return FrameEvent("RX", expected, 3, None), 0.75
        out = run_verified_sequence(transaction)
        self.assertEqual(len(out), 3)
        self.assertEqual(requests, [
            b"\x01M10\x04", b"\x01R6423\x04", b"\x01P010000\x04"
        ])
        self.assertTrue(all(step.redacted()["identity"] == "not_disclosed" for step in out))

    def test_mismatch_aborts_without_followup(self):
        requests = []
        def bad_transaction(request, expected, timeout):
            requests.append(request)
            return FrameEvent("RX", "UNKNOWN_REDACTED", 12), 0.8
        with self.assertRaisesRegex(RuntimeError, "aborted"):
            run_verified_sequence(bad_transaction)
        self.assertEqual(len(requests), 1)

    def test_active_cli_explicit_confirmation(self):
        import hri200_session
        with self.assertRaises(SystemExit) as failure:
            hri200_session.main(["--run-once"])
        self.assertEqual(failure.exception.code, 2)

    def test_discovery_default_does_not_open_serial(self):
        import hri200_session
        fake = {"serial": CANDIDATES[:1], "audio": [], "hid": []}
        with patch.object(hri200_session, "discover", return_value=fake), \
             patch.object(hri200_session, "LinuxCDC") as serial:
            self.assertEqual(hri200_session.main([]), 0)
            serial.assert_not_called()

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux PTY only")
    def test_fake_serial_wire_with_three_replies(self):
        import pty
        import select
        master, slave = pty.openpty()
        name = os.ttyname(slave)
        error = []
        received = []

        def emulated_hri():
            parser = FrameStream("TX")
            try:
                end = time.monotonic() + 3
                while len(received) < 3 and time.monotonic() < end:
                    ready, _, _ = select.select([master], [], [], 0.2)
                    if not ready:
                        continue
                    payload = os.read(master, 1024)
                    for frame in parser.feed(payload):
                        received.append(frame.label)
                        reply = {
                            "M10": b"\x01M10\x04",
                            "R6423": b"\x01R0REDACTED-SYNTHETIC\x04",
                            "P010000": b"\x01B0 0    0000000\x04",
                        }.get(frame.label)
                        if reply is None:
                            raise AssertionError("Unexpected synthetic command")
                        os.write(master, reply)
            except Exception as exc:
                error.append(type(exc).__name__)

        try:
            with LinuxCDC(name) as serial:
                worker = threading.Thread(target=emulated_hri, daemon=True)
                worker.start()
                outcome = run_verified_sequence(serial.transact)
                worker.join(timeout=3)
            self.assertFalse(error, error)
            self.assertEqual(received, ["M10", "R6423", "P010000"])
            self.assertEqual([x.reply for x in outcome], [
                "M10", "R0_REDACTED", "B0_OBSERVED_RESPONSE"
            ])
            self.assertEqual(outcome[-1].rx_bytes, 17)
        finally:
            os.close(slave)
            os.close(master)


if __name__ == "__main__":
    unittest.main()
