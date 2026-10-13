"""Isolated regression tests for the read-only HRI-200 sysfs probe."""
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools'))
from usb_probe import probe, read_attr  # noqa: E402


class UsbProbeTests(unittest.TestCase):
    def test_matching_device_and_multiple_interfaces(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            device = root / '1-1'
            device.mkdir()
            (device / 'idVendor').write_text('26AA\n')
            (device / 'idProduct').write_text('0003\n')
            (device / 'manufacturer').write_text('YAESU\n')
            for number, usb_class in [('0', '01'), ('3', '03')]:
                iface = root / f'1-1:1.{number}'
                iface.mkdir()
                (iface / 'bInterfaceClass').write_text(usb_class + '\n')
            got = probe(root)
            self.assertEqual(len(got), 1)
            self.assertEqual(got[0]['product_id'], '0003')
            self.assertEqual([x['class'] for x in got[0]['interfaces']], ['01', '03'])

    def test_ignores_non_yaesu_vendor_and_other_yaesu_pid(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, vid, pid in [('a', '1234', '0002'), ('b', '26aa', '4321')]:
                dev = root / name
                dev.mkdir()
                (dev / 'idVendor').write_text(vid)
                (dev / 'idProduct').write_text(pid)
            self.assertEqual(probe(root), [])
            self.assertEqual(len(probe(root, product_ids=None)), 1)

    def test_missing_sysfs_safe(self):
        self.assertEqual(probe(Path('/path/that/does/not/exist/test_usb_probe')), [])
        self.assertIsNone(read_attr(Path('/path/that/does/not/exist'), 'missing'))


if __name__ == '__main__':
    unittest.main()
