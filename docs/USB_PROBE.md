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

### Sysfs ALSA card interface path confirmed

Operator executed a read-only command on the Raspberry Pi 4:

```text
# readlink -f /sys/class/sound/card0/device
/sys/devices/platform/scb/fd500000.pcie/pci0000:00/0000:00:00.0/0000:01:00.0/usb1/1-1/1-1.3/1-1.3.2/1-1.3.2:1.0
```

This confirms that the ALSA card's `device` symlink resolves to a **USB interface** (`1-1.3.2:1.0`), whose **immediate USB device parent** is `1-1.3.2`. Together with the earlier `udevadm --attribute-walk` evidence on the same audio PCM device (`26aa:0003`), this validates the parent traversal strategy planned in `tools/hri200_discovery.py`.

Do not hardcode `card0`, USB topology addresses (`1-1.3.2`), `/sys/devices/platform/scb`, or controller paths: they are observations of one system at one moment.

**Still pending:** run the Python discovery tool against the Raspberry Pi (no I/O), verify the serial device symlink topology, test cross-platform mocks and then separately evaluate actual audio/HRI control. Neither this path nor the present ALSA status demonstrates WIRES-X network connectivity.

**Next single read-only check:** `readlink -f /sys/class/tty/ttyACM0/device` to inspect the USB interface ancestry for the already-identified YAESU serial endpoint.

### Serial sysfs USB interface ancestry confirmed

Read-only physical Raspberry Pi 4 output:

```text
# readlink -f /sys/class/tty/ttyACM0/device
/sys/devices/platform/scb/fd500000.pcie/pci0000:00/0000:00:00.0/0000:01:00.0/usb1/1-1/1-1.3/1-1.3.1/1-1.3.1:1.0
```

The serial tty resolves to USB interface `1-1.3.1:1.0`, under USB device `1-1.3.1` (previously identified using `udevadm` as YAESU `26aa:0002`). The audio ALSA card resolved to USB interface `1-1.3.2:1.0`, under USB device `1-1.3.2` (previously confirmed as YAESU `26aa:0003`).

These two devices attach to the same upstream hub `1-1.3`, but **sharing a hub alone is insufficient proof of physical unit pairing on a multi-unit system**. Portable discovery must independently validate each device's USB parent identities and handle multiple candidates explicitly. Neither the host-specific paths nor device numbers are suitable as defaults.

The sysfs ancestor traversal used by `tools/hri200_discovery.py` is structurally consistent with both observed links. The script is not yet verified by execution on the physical Raspberry Pi. Next safe gate: check Python availability, then review how to transfer and execute the read-only script, with operator approval for any disk modifications.

### Real Raspberry Pi run of the repository discovery tool

The operator fetched the published repository script (4,466 bytes) into `/tmp/hri200_discovery.py` and ran it **read-only** via:

```sh
python3 -B /tmp/hri200_discovery.py
```

Reported Python version: **3.13.5**. The complete resulting JSON was:

```json
{
  "audio": [
    {
      "alsa_id": "codec",
      "card": "card0",
      "pcm": {
        "capture": ["/dev/snd/pcmC0D0c"],
        "playback": ["/dev/snd/pcmC0D0p"]
      },
      "pid": "0003",
      "usb_port": "1-1.3.2",
      "usb_product": "HRI-200 A(CH1) USB Audio codec",
      "vid": "26aa"
    }
  ],
  "note": "Candidate enumeration only; no hardware I/O or proven physical USB pairing.",
  "schema": "hri200-linux-discovery-v1",
  "serial": [
    {
      "device": "/dev/ttyACM0",
      "pid": "0002",
      "usb_port": "1-1.3.1",
      "usb_product": "HRI-200 Communication device A",
      "vid": "26aa"
    }
  ],
  "status": "one_serial_one_audio_candidate"
}
```

**Verified real-hardware milestone:** the **actual GitHub implementation** successfully enumerated the HRI-200 communication and sound interfaces on a Raspberry Pi 4 using Linux sysfs, without hardcoding numerical tty/ALSA card identifiers. The result exposes one serial candidate and one audio candidate. PCM playback and capture device names are enumerated, not opened or tested.

**Explicit limitations:** driver recognition does not prove physical pairing in a multi-unit setup, serial command framing, bidirectional HRI audio streams, PTT/HID functionality, or compatibility with proprietary YAESU WIRES-X networking. No USB device file was opened, no RF TX, no new daemon installed, no TETRA service change. A temporary copy of the script was downloaded to `/tmp` by the operator; the script itself performed no device I/O.

**License/publication follow-up:** public-repository content and attribution terms are under review; adding LICENSE/NOTICE will require confirmation of the intended copyright holder and license selection.

### Real HID sysfs instance found on Raspberry Pi

The operator executed this **read-only** command on the running Raspberry Pi 4:

```sh
find /sys/bus/hid/devices -maxdepth 1 -iname '*26AA:0003*' -printf '%f\n'
```

Result:

```text
0003:26AA:0003.0001
```

Interpretation: Linux HID bus `0003` exposes an HRI-200 audio/composite device `VID:PID 26aa:0003` as HID instance `0001`. Together with the previously observed `usbhid` binding, this confirms **enumeration of the HID interface**, not accessible `hidraw`, report descriptor interpretation, HID command semantics, PTT or WIRES-X session functionality. The instance suffix is not stable and should never be hardcoded.

**Next single read-only hardware check:** list `/sys/bus/hid/devices/0003:26AA:0003.0001/hidraw/` to see whether a `hidrawN` class node is exposed (do not open the node). Follow with offline HID report-descriptor inspection under explicit review before any command writes.

### HRI-200 HIDRAW sysfs class instance confirmed

Read-only operator output from Raspberry Pi 4:

```text
# ls -l /sys/bus/hid/devices/0003:26AA:0003.0001/hidraw/
total 0
drwxr-xr-x 3 root root 0 Oct 13 23:58 hidraw0
```

**Evidence:** Linux exposes a `hidraw0` class child under HID device `0003:26AA:0003.0001`. The HID interface was already observed as bound to `usbhid`; this strengthens the discovery evidence, but does **not** prove that `/dev/hidraw0` is currently present/accessible, and does not prove any HID report or command exchange. The HID instance suffix and `hidrawN` index are transient.

**Proposed next non-invasive step:** read the cached **HID report descriptor** from sysfs with `od -An -tx1 -v /sys/bus/hid/devices/0003:26AA:0003.0001/report_descriptor`. This accesses a kernel sysfs attribute, not the `/dev/hidraw0` node, does not write device controls, does not assert PTT and should not affect ongoing TETRA services. Interpret with care: advertised HID report structure alone does not establish report semantics, command values, packet framing or YAESU WIRES-X compatibility. Keep read-only until separately authorized.

### HRI-200 HID report descriptor decoded (read-only)

The operator read the cached kernel HID report descriptor through sysfs, without opening `/dev/hidraw*`:

```sh
od -An -tx1 -v /sys/bus/hid/devices/0003:26AA:0003.0001/report_descriptor
```

Exact **31-byte** output:

```text
05 0c 09 01 a1 01 15 00 25 01 09 e9 09 ea 75 01
95 02 81 2a 09 e2 95 01 81 2e 95 05 81 01 c0
```

#### Standard USB HID interpretation

| Bytes | HID item | Meaning |
| --- | --- | --- |
| `05 0c` | Usage Page (Consumer) | Standard Consumer usage page `0x0C` |
| `09 01` | Usage (Consumer Control) | Consumer Control application |
| `a1 01` | Collection (Application) | Begin application collection |
| `15 00`, `25 01` | Logical Min/Max | Values 0 and 1 |
| `09 e9`, `09 ea` | Consumer Usage | Volume Increment and Volume Decrement |
| `75 01`, `95 02`, `81 2a` | Report Size/Count/Input | Two 1-bit input fields, low bits 0 and 1 |
| `09 e2`, `95 01`, `81 2e` | Consumer Usage, count and Input | One 1-bit Mute input field, bit 2 |
| `95 05`, `81 01` | Count/Input (Constant) | Five constant padding bits, bits 3–7 |
| `c0` | End Collection | Closes application collection |

No Report ID item appears, and there is only one declared input report, whose **payload is one byte (8 bits)**. There are no Output or Feature report declarations in this descriptor.

**Engineering consequence:** the HID interface declares standard Consumer Volume+/Volume−/Mute input usage. It is **not evidence** that HID carries PTT, COS/COR, connection control, WIRES-X session commands or radio control. Even actual delivery of these inputs is not proven by a cached descriptor alone. Do not infer proprietary control commands or send trial HID output reports to this interface.

**Project direction:** do not invest in speculative HID PTT writes. Keep this HID as a read-only optional device in portable discovery; focus future control-protocol research on documented/observed interactions with the separate CDC ACM serial interface in a safely isolated environment. Live CDC control, DTR/RTS and audio I/O remain outside the current authorization.

**Next safe path confirmation:** `readlink -f /sys/class/hidraw/hidraw0/device`, to validate sysfs ancestry for portable future HID discovery. `hidraw0` is this host's current name only, not a hardcoded application setting.


### HIDRAW USB ancestry verified and discovery tool extended

Operator ran the following command on the Raspberry Pi 4:

```sh
readlink -f /sys/class/hidraw/hidraw0/device
```

Kernel sysfs returned:

```text
/sys/devices/platform/scb/fd500000.pcie/pci0000:00/0000:00:00.0/0000:01:00.0/usb1/1-1/1-1.3/1-1.3.2/1-1.3.2:1.3/0003:26AA:0003.0001
```

The HIDRAW class node points to HID instance `0003:26AA:0003.0001` beneath USB interface `1-1.3.2:1.3`, itself a child of the same YAESU `26aa:0003` USB device `1-1.3.2` as the independently confirmed ALSA audio card (`1-1.3.2:1.0`). This is **strong evidence for common USB-device parentage of AUDIO and HID**. Serial remains a distinct `26aa:0002` USB device (`1-1.3.1`). On hosts with multiple HRI-200 units, common upstream hub attachment alone **must not** be treated as proof that any particular 0002/0003 pair is one physical unit.

**Code change (not yet tested on hardware):** `tools/hri200_discovery.py` now also scans `/sys/class/hidraw/hidrawN/device`, walks sysfs ancestry to `26aa:0003` and inventories `/dev/hidrawN` by name. The JSON output adds a `hid` collection and schema marker `hri200-linux-discovery-v2`, with `audio_cards_same_usb_device` for matches to the **same** 0003 parent. Existing `status` still describes serial/audio candidates; HID is optional. The tool **never opens** the HIDRAW character device, serial port or audio PCM. Unit tests use synthetic sysfs trees and remain subject to execution/validation.

**Next safe hardware milestone:** fetch the updated script from GitHub (no daemon/install) into `/tmp` and run it via `python3 -B` read-only; the operator must approve each command. `hidraw0` and the sysfs topology are observations, not defaults.
