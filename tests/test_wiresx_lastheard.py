# Copyright 2026 IU0NDT
# SPDX-License-Identifier: Apache-2.0
"""Synthetic, offline tests: no HRI-200, RF, YAESU network or private logs."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from wiresx_lastheard import parse_log, valid_coordinates


def line(name, identifier, call, when, channel="Room", gps=""):
    return "%".join((name, identifier, call, when, channel, "0" * 36, gps, "0", "", "", "", "", ""))


class LastHeardTests(unittest.TestCase):
    def test_real_capture_shape_without_real_data(self):
        content = "\n".join([
            line("private1", "r001", "TEST1", "2026/10/15 11:55:20", gps='N:39 08\' 34" / E:012 10\' 03"'),
            line("private2", "r002", "TEST2", "2023/01/10 13:22:00"),
            line("private3", "r003", "TEST3", "2000/01/01 00:00:00"),
            line("private4", "r004", "TEST4", "not-a-date"),
            "bad%line",
        ])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "WiresAccess.log"
            path.write_text(content, encoding="utf-8")
            data = parse_log(path, secret=b"test-secret")
            again = parse_log(path, secret=b"test-secret")
        s = data["summary"]
        self.assertEqual(s["total_rows"], 5)
        self.assertEqual(s["parsed_rows"], 3)
        self.assertEqual(s["malformed_rows"], 1)
        self.assertEqual(s["invalid_dates"], 1)
        self.assertEqual(s["year_2000_candidate_placeholder"], 1)
        self.assertEqual(s["other_dated_rows"], 2)
        self.assertEqual(s["records_with_valid_coordinates"], 1)
        self.assertEqual(s["latest_non_2000_received"], "2026-10-15 11:55:20")
        self.assertEqual(s["receive_channels"], {"Room": 3})
        self.assertEqual(again["rows"], data["rows"])
        self.assertTrue(data["rows"][0]["station"].startswith("ST-"))
        self.assertNotIn("TEST1", str(data))
        self.assertNotIn("private1", str(data))
        self.assertNotIn("r001", str(data))
        self.assertNotIn("39 08", str(data))
        self.assertFalse(data["live_rx_tx"])

    def test_optional_callsigns_only(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "log.txt"
            path.write_text(line("private1", "secret-radio-id", "TEST123", "2024/01/02 10:00:00"))
            data = parse_log(path, secret=b"salt", show_callsigns=True)
        self.assertEqual(data["rows"][0]["station"], "TEST123")
        self.assertNotIn("secret-radio-id", str(data))

    def test_gps_validation(self):
        self.assertTrue(valid_coordinates('N:39 08\' 34" / E:012 10\' 03"'))
        self.assertFalse(valid_coordinates('N:99 08\' 34" / E:012 10\' 03"'))
        self.assertFalse(valid_coordinates('N:39 60\' 34" / E:012 10\' 03"'))
        self.assertFalse(valid_coordinates('N:39 08\' 34" / E:181 10\' 03"'))
        self.assertFalse(valid_coordinates("sensitive string"))

    def test_truncation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "log.txt"
            path.write_text("\n".join(
                line(f"name{i}", f"{i}", f"TEST{i}", "2025/01/02 10:00:00")
                for i in range(4)
            ))
            data = parse_log(path, secret=b"salt", limit=2)
        self.assertTrue(data["truncated"])
        self.assertEqual(len(data["rows"]), 2)
        self.assertEqual(data["summary"]["total_rows"], 4)


if __name__ == "__main__":
    unittest.main()
