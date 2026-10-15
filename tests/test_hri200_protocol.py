# Copyright 2026 IU0NDT
# SPDX-License-Identifier: Apache-2.0
"""Synthetic offline tests for the passive HRI-200 stream engine."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))
from hri200_protocol import FrameStream, PassiveSession, classify


class FrameTests(unittest.TestCase):
    def test_known_patterns_without_decoding_semantics(self):
        self.assertEqual(classify(b"P010000"), "P010000")
        self.assertEqual(classify(b"D1V0000"), "D1V0000")
        self.assertEqual(classify(b"B0 0    0000000"), "B0_OBSERVED_RESPONSE")
        self.assertEqual(classify(b"B0_OTHER_UNVERIFIED"), "UNKNOWN_REDACTED")

    def test_split_across_transfers(self):
        parser = FrameStream("TX")
        self.assertEqual(parser.feed(b"\x01P01"), [])
        self.assertTrue(parser.incomplete)
        found = parser.feed(b"0000\x04", 1.0)
        self.assertEqual([item.label for item in found], ["P010000"])
        self.assertFalse(parser.incomplete)

    def test_multiple_frames_and_noise(self):
        parser = FrameStream("RX")
        found = parser.feed(b"discard\x04\x01M10\x04\x01B0 0    0000000\x04", 2.0)
        self.assertEqual([event.label for event in found], ["M10", "B0_OBSERVED_RESPONSE"])
        self.assertEqual(parser.stats["frames"], 2)
        self.assertEqual(parser.stats["ignored_outside_frame"], len(b"discard\x04"))

    def test_restart_after_nested_stx(self):
        parser = FrameStream("TX")
        found = parser.feed(b"\x01garbled\x01M10\x04")
        self.assertEqual([e.label for e in found], ["M10"])
        self.assertEqual(parser.stats["resync"], 1)

    def test_oversize_bounded_discard_until_end(self):
        parser = FrameStream("TX", max_body=3)
        found = parser.feed(b"\x01XXXXXX\x04\x01M10\x04")
        self.assertEqual([e.label for e in found], ["M10"])
        self.assertEqual(parser.stats["oversized"], 1)
        self.assertFalse(parser.incomplete)

    def test_redaction_does_not_expose_sensitive_identity(self):
        private = b"R0" + b"SECRET,IDENTITY,SECRET".hex().encode("ascii")
        parser = FrameStream("RX")
        events = parser.feed(b"\x01" + private + b"\x04")
        self.assertEqual([e.label for e in events], ["R0_REDACTED"])
        self.assertNotIn("SECRET", repr(events))
        self.assertNotIn("IDENTITY", repr(events))
        self.assertNotIn("534543524554", repr(events))
        self.assertFalse(hasattr(events[0], "payload"))

    def test_invalid_direction(self):
        with self.assertRaises(ValueError):
            FrameStream("SIDEWAYS")
        with self.assertRaises(ValueError):
            PassiveSession().observe("SIDEWAYS", b"\x01M10\x04")

    def test_partial_buffers_separate_rx_tx(self):
        session = PassiveSession()
        self.assertEqual(session.observe("TX", b"\x01P010"), [])
        self.assertEqual(session.observe("RX", b"\x01M10\x04")[0].label, "M10")
        self.assertEqual(session.observe("TX", b"000\x04")[0].label, "P010000")
        self.assertEqual(session.report()["tx_frames"], 1)
        self.assertEqual(session.report()["rx_frames"], 1)

    def test_fifo_latencies_from_observation_only(self):
        session = PassiveSession()
        request = b"\x01P010000\x04"
        reply = b"\x01B0 0    0000000\x04"
        session.observe("TX", request, 1.0)
        session.observe("RX", reply, 1.0007)
        session.observe("TX", request, 2.0)
        session.observe("RX", reply, 2.0012)
        result = session.report()
        self.assertEqual(result["poll_response_fifo"]["pairs"], 2)
        self.assertEqual(result["poll_response_fifo"]["unpaired_requests"], 0)
        self.assertAlmostEqual(result["poll_response_fifo"]["mean_ms"], 0.95, places=2)
        self.assertEqual(result["observed_frames"]["TX:P010000"], 2)
        self.assertEqual(result["observed_frames"]["RX:B0_OBSERVED_RESPONSE"], 2)

    def test_synthetic_full_exchange(self):
        session = PassiveSession()
        session.observe("TX", b"\x01M10\x04\x01R6423\x04")
        session.observe("RX", b"\x01M10\x04\x01R0PRIVATE\x04")
        session.observe("TX", b"\x01D1V0000\x04")
        result = session.report()
        self.assertEqual(result["tx_frames"], 3)
        self.assertEqual(result["rx_frames"], 2)
        self.assertEqual(result["observed_frames"]["RX:R0_REDACTED"], 1)
        self.assertNotIn("PRIVATE", repr(result))

    def test_pending_capacity_limit(self):
        session = PassiveSession(max_pending_polls=2)
        for ts in (1.0, 2.0, 3.0):
            session.observe("TX", b"\x01P010000\x04", ts)
        report = session.report()
        self.assertEqual(report["poll_response_fifo"]["unpaired_requests"], 2)
        self.assertEqual(report["observed_frames"]["dropped_pending_poll"], 1)


if __name__ == "__main__":
    unittest.main()
