"""Offline unit tests: synthetic ZIPs only, no proprietary software."""
import io
import tempfile
import unittest
import zipfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from archive_inventory import inventory, signature


class ArchiveInventoryTests(unittest.TestCase):
    def test_signatures(self):
        self.assertEqual(signature(b"MZ\x00\x00"), "PE/DOS executable header")
        self.assertEqual(signature(b"%PDF-1.6"), "PDF")
        self.assertEqual(signature(b"MSCF\x00"), "CAB archive")

    def test_zip_inventory_hashes_without_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "example.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("firmware/dummy.exe", b"MZ" + b"\0" * 8)
                archive.writestr("manual.pdf", b"%PDF-1.4\n")
                archive.writestr("../../../should-not-be-extracted.txt", b"safe")
            got = inventory(path)
            self.assertEqual(got["file_count"], 3)
            self.assertEqual(got["total_uncompressed"], 23)
            self.assertEqual(got["members"][0]["file_signature"], "PE/DOS executable header")
            self.assertEqual(len(got["archive_sha256"]), 64)
            self.assertFalse((Path(tmp).parent / "should-not-be-extracted.txt").exists())

    def test_member_limit_rejects_large_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "limits.zip"
            with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("data", b"a" * 4096)
            with self.assertRaisesRegex(ValueError, "Member exceeds limit"):
                inventory(path, max_member=32)

    def test_total_limit_rejects_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "limits.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("first", b"123")
                archive.writestr("second", b"456")
            with self.assertRaisesRegex(ValueError, "total uncompressed"):
                inventory(path, max_total=5)


if __name__ == "__main__":
    unittest.main()
