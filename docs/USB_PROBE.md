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

On Windows the verified devices were vendor 26AA with products 0002 (CDC communication) and 0003 (USB composite audio/HID). On a Raspberry Pi 4 Linux host, `lsusb -t` has now **confirmed kernel driver bindings** for `cdc_acm`, `snd-usb-audio` and `usbhid` (see below). Communication, streaming and WIRES-X protocol behavior remain untested.

Do not move a live HRI-200 away from an operating Windows station or run any Linux install/restart command until an explicit maintenance window is approved.

### Physical Raspberry Pi 4 test (2026-10-13)

The test was performed on a Raspberry Pi 4 already hosting a TETRA system, with no driver installation or changes to its running services. Operator-provided read-only output:

```text
$ lsusb -d 26aa:
Bus 001 Device 005: ID 26aa:0003 Yaesu Musen HRI-200 A(CH1) USB Audio codec
Bus 001 Device 006: ID 26aa:0002 Yaesu Musen HRI-200 Communication device A

$ lsusb -t
... Bus 001 Dev 006 If 0 Class=Communications Driver=cdc_acm 12M
... Bus 001 Dev 006 If 1 Class=CDC Data Driver=cdc_acm 12M
... Bus 001 Dev 005 If 0 Class=Audio Driver=snd-usb-audio 12M
... Bus 001 Dev 005 If 1 Class=Audio Driver=snd-usb-audio 12M
... Bus 001 Dev 005 If 2 Class=Audio Driver=snd-usb-audio 12M
... Bus 001 Dev 005 If 3 Class=Human Interface Device Driver=usbhid 12M
```

**Verified:** this Linux host enumerates the Yaesu HRI-200 CDC, audio and HID interfaces with standard in-kernel drivers, on a Full Speed (12 Mbit/s) USB connection.

**Not verified:** the assignment of a usable `/dev/ttyACM*` character device, ALSA audio capture/playback, HID reports, any HRI-200 command exchanges, PTT, RF, Internet registration, or WIRES-X room operation.

**Next read-only check:** `ls -l /dev/ttyACM*` to see the corresponding serial device, with no opening, line control, or writes to the device. Avoid mapping the runtime to a fixed tty number: hotplug and multi-adapter hosts can renumber devices. A stable discovery policy will be designed after this check.

### CDC ACM character device available (2026-10-13)

Operator's subsequent read-only Linux command:

```text
# ls -l /dev/ttyACM*
crw-rw---- 1 root dialout 166, 0 Oct 13 23:58 /dev/ttyACM0
```

The Linux host exposes at least one ACM serial character device, `/dev/ttyACM0`, major/minor `166:0`, owned by `root:dialout`. This is consistent with the YAESU `cdc_acm` driver binding observed immediately before, but a per-device sysfs parent check is still required to **prove the association unambiguously** if other CDC hardware is attached. This is **not** evidence that the proprietary HRI-200 command protocol has been discovered or that a WIRES-X session works.

Do not embed `/dev/ttyACM0` as a fixed path in the final program; interface discovery must resolve a stable hardware identity at runtime. No serial device was opened or written to in this test.

**Next independent gate:** identify ALSA sound cards via `cat /proc/asound/cards` (read-only); later map the selected ALSA card's sysfs USB parent to vendor `26aa` and product `0003`.
