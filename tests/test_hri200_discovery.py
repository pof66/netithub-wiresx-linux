# Copyright 2026 IU0NDT
# SPDX-License-Identifier: Apache-2.0
# Source: https://github.com/pof66/netithub-wiresx-linux

"""Offline regression tests for sysfs-only serial/audio/HID discovery."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from hri200_discovery import discover  # noqa: E402


def usb(root: Path, name: str, vid: str, pid: str) -> Path:
    parent = root / "devices" / "usb1" / name
    parent.mkdir(parents=True)
    (parent / "idVendor").write_text(vid)
    (parent / "idProduct").write_text(pid)
    (parent / "product").write_text("Example USB device\n")
    interface = parent / (name + ":1.0")
    interface.mkdir()
    return interface


def serial(root: Path, name: str, target: Path) -> None:
    entry = root / "class" / "tty" / name
    entry.mkdir(parents=True)
    (entry / "device").symlink_to(target, target_is_directory=True)


def audio(root: Path, number: int, target: Path) -> None:
    base = root / "class" / "sound"
    card = base / ("card" + str(number))
    card.mkdir(parents=True)
    (card / "device").symlink_to(target, target_is_directory=True)
    (card / "id").write_text("codec\n")
    for suffix in ("c", "p"):
        (base / f"pcmC{number}D0{suffix}").mkdir()


def hidraw(root: Path, name: str, usb_interface: Path) -> None:
    """Create fake HID node nested under the device's USB interface."""
    hid_instance = usb_interface / "0003:26AA:0003.0001"
    hid_instance.mkdir()
    entry = root / "class" / "hidraw" / name
    entry.mkdir(parents=True)
    (entry / "device").symlink_to(hid_instance, target_is_directory=True)


class DiscoveryTests(unittest.TestCase):
    def test_one_serial_and_one_audio_with_non_yaesu_device(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            serial(root, "ttyACM4", usb(root, "1-1.3.1", "26aa", "0002"))
            serial(root, "ttyACM5", usb(root, "1-1.3.3", "0451", "2046"))
            audio(root, 7, usb(root, "1-1.3.2", "26aa", "0003"))
            result = discover(root / "class")
            self.assertEqual(result["status"], "one_serial_one_audio_candidate")
            self.assertEqual([x["device"] for x in result["serial"]], ["/dev/ttyACM4"])
            self.assertEqual([x["card"] for x in result["audio"]], ["card7"])
            self.assertEqual(result["audio"][0]["pcm"]["capture"], ["/dev/snd/pcmC7D0c"])
            self.assertEqual(result["audio"][0]["pcm"]["playback"], ["/dev/snd/pcmC7D0p"])
            self.assertEqual(result["audio"][0]["alsa_id"], "codec")

    def test_multiple_devices_are_not_auto_paired(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            serial(root, "ttyACM0", usb(root, "1-1.1", "26aa", "0002"))
            serial(root, "ttyACM1", usb(root, "1-1.2", "26aa", "0002"))
            audio(root, 0, usb(root, "1-1.3", "26aa", "0003"))
            got = discover(root / "class")
            self.assertEqual(got["status"], "operator_selection_required")
            self.assertEqual(len(got["serial"]), 2)

    def test_hidraw_matches_exact_usb_audio_parent_and_excludes_non_yaesu(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            serial(root, "ttyACM9", usb(root, "1-2.1", "26aa", "0002"))
            audio_iface = usb(root, "1-2.2", "26aa", "0003")
            audio(root, 2, audio_iface)
            hidraw(root, "hidraw7", audio_iface)
            wrong = usb(root, "1-2.3", "2109", "3431")
            hidraw(root, "hidraw8", wrong)
            result = discover(root / "class")
            self.assertEqual(result["schema"], "hri200-linux-discovery-v2")
            self.assertEqual(result["status"], "one_serial_one_audio_candidate")
            self.assertEqual(len(result["hid"]), 1)
            self.assertEqual(result["hid"][0]["device"], "/dev/hidraw7")
            self.assertEqual(result["hid"][0]["usb_port"], "1-2.2")
            self.assertEqual(result["hid"][0]["hid_instance"], "0003:26AA:0003.0001")
            self.assertEqual(result["hid"][0]["audio_cards_same_usb_device"], ["card2"])

    def test_hidraw_optional_for_serial_audio_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            serial(root, "ttyACM0", usb(root, "1-1.1", "26aa", "0002"))
            audio(root, 0, usb(root, "1-1.2", "26aa", "0003"))
            result = discover(root / "class")
            self.assertEqual(result["hid"], [])
            self.assertEqual(result["status"], "one_serial_one_audio_candidate")

    def test_no_devices_and_missing_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(discover(root / "class")["status"], "missing_endpoint")
            serial(root, "ttyACM0", usb(root, "1-1.1", "26aa", "0002"))
            self.assertEqual(discover(root / "class")["status"], "missing_endpoint")

    def test_nonmatching_usb_boundary_not_crossed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hub = root / "devices" / "usb1" / "1-1"
            hub.mkdir(parents=True)
            (hub / "idVendor").write_text("26aa")
            (hub / "idProduct").write_text("0002")
            other = hub / "1-1.4"
            other.mkdir()
            (other / "idVendor").write_text("2109")
            (other / "idProduct").write_text("3431")
            iface = other / "1-1.4:1.0"
            iface.mkdir()
            serial(root, "ttyACM0", iface)
            self.assertEqual(discover(root / "class")["serial"], [])


if __name__ == "__main__":
    unittest.main()
