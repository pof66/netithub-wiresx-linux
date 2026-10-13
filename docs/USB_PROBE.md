# Read-only HRI-200 USB discovery on Linux

**Scope:** This initial tool identifies USB device descriptors, interfaces and kernel driver names through the Linux sysfs filesystem. It does not establish WIRES-X network connections or send serial/HID/audio commands.

## Requirements

- Linux with sysfs mounted (e.g. Debian or Raspberry Pi OS).
- Python 3.10+ standard library; no pip packages, root access, udev rules or software installation required.

Run from a local checkout:

```sh
python3 tools/usb_probe.py
```

To view all USB product IDs for the detected YAESU vendor:

```sh
python3 tools/usb_probe.py --all-products
```

For offline testing with a mock sysfs root:

```sh
python3 tools/usb_probe.py --sysfs-root /path/to/mock-sysfs
```

Run the unit tests (uses temporary fake sysfs and no hardware):

```sh
python3 -m unittest discover -s tests -v
```

No `sudo` is expected. This utility does not open anything in `/dev`, does not read the device serial number, and does not run programs, restart services, flash firmware, transmit RF or contact the internet.

### Expected outputs

`devices` contains zero or more matching YAESU HRI-200 USB devices. An empty result might mean no connected device, no sysfs support, or insufficient read access — **it is not proof that HRI-200 is Linux-incompatible**.

On Windows the verified devices were vendor 26AA with products 0002 (CDC communication) and 0003 (USB composite audio/HID). On Linux the corresponding interface drivers (`cdc_acm`, `snd-usb-audio`, `usbhid`) are **hypotheses pending a physical test**.

Do not move a live HRI-200 away from an operating Windows station or run any Linux install/restart command until an explicit maintenance window is approved.
