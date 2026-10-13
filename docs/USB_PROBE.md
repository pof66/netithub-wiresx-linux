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

### ALSA card registered on Raspberry Pi 4 (2026-10-13)

The operator ran a read-only ALSA inventory command:

```text
# cat /proc/asound/cards
 0 [codec          ]: USB-Audio - HRI-200 A(CH1) USB Audio codec
                      YAESU MUSEN Co., Ltd. HRI-200 A(CH1) USB Audio codec at usb-0000:01:00.0-1.3.2,
```

**Confirmed:** the Linux ALSA subsystem has registered the YAESU HRI-200 USB Audio codec with ALSA card ID `codec` and currently assigned card index `0`. This corroborates the `snd-usb-audio` driver binding seen in `lsusb -t`.

**Not yet confirmed:** USB audio PCM stream direction, accessible sound formats, capture/playback operation, latency or interaction with WIRES-X control. Do not assume that card index `0` is stable across reboots/hotplug or use it as a portable default.

**Next read-only inspection:** `cat /proc/asound/card0/stream0` (only for this observed session) to view the USB audio streaming descriptors and supported formats without starting any stream, recording or playback.

### USB PCM stream descriptors (2026-10-13)

Read-only kernel information from `cat /proc/asound/card0/stream0` (ALSA card `0` was the HRI-200 in this session):

| Direction | Status | USB interface/altset | Format | Channels | Endpoint | Synchronization |
| --- | --- | --- | --- | --- | --- | --- |
| Playback (host to HRI-200) | Stop | Interface 2, Altset 1 | S16_LE, 16-bit | 2 (FL, FR) | 0x02 OUT | ADAPTIVE |
| Capture (HRI-200 to host) | Stop | Interface 1, Altset 1 | S16_LE, 16-bit | 1 (MONO) | 0x81 IN | ASYNC |

Both interfaces enumerate these discrete sample rates (Hz): **8000, 11025, 16000, 22050, 32000, 44100, 48000**.

This confirms that standard kernel USB/ALSA drivers expose **descriptors for both capture and playback**, not that real PCM audio has been recorded/playback-tested. No stream was started in this test. No PTT was enabled, and the functions of left/right playback channels are not established. Do not assume 16-bit PCM over USB is the same as native C4FM speech frames or YAESU's proprietary room protocol.

**Architecture consequence:** implement an ALSA adapter with runtime USB device identification (avoid `hw:0` and fixed card indices), sample-format negotiation and optional explicit channel selection/downmix/upmix/resampling. Keep audio transport separate from control (serial/HID) and from future WIRES-X network signaling. Default TX disabled.

**Next read-only check:** `cat /proc/asound/pcm` to enumerate ALSA PCM logical devices and directions; do not start `arecord` or `aplay` on this shared TETRA host during descriptor-only diagnostics.

### ALSA PCM logical device confirmed (operator read-only test)

The operator ran `cat /proc/asound/pcm` after the previously observed HRI-200 USB audio card registration:

```text
00-00: USB Audio : USB Audio : playback 1 : capture 1
```

**Meaning:** ALSA currently exposes a playback-capable PCM subdevice and a capture-capable PCM subdevice under card 0, device 0. In this same session card 0 was identified as the HRI-200 USB Audio codec. These are two logical stream directions, not proof that both streams have passed actual audio.

This confirms the driver-level discoverability gate. **Still untested:** opening PCM, audio integrity, latency, TX/PTT wiring, serial/HID command frames, and native connections to YAESU WIRES-X rooms.

**Portability rule:** Never assume `hw:0,0` or `/dev/ttyACM0` is stable. Resolve the sound/serial interfaces from matching USB parent identity and inspect capabilities dynamically.

**Next read-only test:** Verify the kernel-reported USB vendor/product identity of the current serial interface using a filtered `udevadm info` query. Do not open the port or assert DTR/RTS on the shared TETRA host.

### Serial port USB parent identity positively established

Read-only output from `udevadm info -q property -n /dev/ttyACM0` (filtered to USB identity and driver fields):

```text
ID_MODEL_ID=0002
ID_VENDOR_ID=26aa
ID_USB_INTERFACE_NUM=00
ID_USB_DRIVER=cdc_acm
```

This **directly confirms** that the currently observed `/dev/ttyACM0` is the HRI-200 communication device A (`26aa:0002`, USB interface 00), not merely an arbitrary serial device. The name `ttyACM0` is ephemeral and must not be stored as a deployment invariant.

**Portable discovery requirement:** at startup resolve eligible tty character devices by authoritative sysfs/udev USB ancestry (`idVendor=26aa`, `idProduct=0002`, interface 00), detect ambiguity rather than choosing the first match, expose explicit operator selection where two identical interfaces exist and never open the serial device during the read-only discovery phase. These are discovery selectors, not a valid WIRES-X session protocol.

**Next hardware inventory gate:** read the current ALSA capture device udev metadata without opening audio (`/dev/snd/pcmC0D0c` as observed *only on this host at this time*). Afterwards design discovery by USB identity rather than ALSA numerical card index.

### ALSA USB parent verification (Raspberry Pi operator output)

The PCM capture endpoint `/dev/snd/pcmC0D0c` did not directly carry `ID_VENDOR_ID` and `ID_MODEL_ID` in its `udevadm info -q property` output. Walking the **sysfs ancestor chain**, using:

```sh
udevadm info --attribute-walk --name=/dev/snd/pcmC0D0c | grep -E 'ATTRS\{(idVendor|idProduct|product)\}'
```

revealed:

```text
ATTRS{idProduct}=="0003"
ATTRS{idVendor}=="26aa"
ATTRS{product}=="HRI-200 A(CH1) USB Audio codec                    "
ATTRS{idProduct}=="2046"
ATTRS{idVendor}=="0451"
ATTRS{idProduct}=="3431"
ATTRS{idVendor}=="2109"
ATTRS{product}=="USB2.0 Hub"
ATTRS{idProduct}=="0002"
ATTRS{idVendor}=="1d6b"
ATTRS{product}=="xHCI Host Controller"
```

This positively identifies the USB ancestor of the ALSA PCM endpoint as **YAESU 26aa:0003**, and also shows upstream intermediate USB hub and host controller identities that **must not be confused with HRI-200 endpoints**.

### Portable endpoint inventory implementation

`tools/hri200_discovery.py` performs **read-only** sysfs ancestor matching separately for:

- serial: USB VID/PID `26aa:0002`, Linux CDC `ttyACM*`
- audio: USB VID/PID `26aa:0003`, Linux ALSA `cardN` and PCM device names

No driver installation, USB endpoint opening, ALSA streaming, firmware changes, serial control, network authentication, or RF transmission. If multiple matching endpoints are detected, it reports that **operator selection is required**, rather than incorrectly pairing devices by shared hub or arbitrary enumeration order. Output paths/card indices are *observations* and never deployment defaults.

```sh
python3 tools/hri200_discovery.py
```

The local TETRA machine is not modified merely by reading this script's source on GitHub; running it on the host is an explicit next action after the operator decides to fetch the repository. Synthetic tests are in `tests/test_hri200_discovery.py`.
