# HRI-200 protocol core: first independent Linux building block

**Status: passive, offline, no hardware I/O.** This is a protocol framing engine, not a working WIRES-X node. The dashboard is not part of this milestone.

## Confirmed observations

The operator captured the original Windows WIRES-X 2.010 communicating with an HRI-200 A (USB VID:PID 26AA:0002) and successfully ran tools/hri200_pcap_decode.py against the private USBPcap file. Results:

- 1,164 USBPcap records; 572 bulk payload records; 572 frames.
- Start delimiter 0x01, end delimiter 0x04; in this one capture every selected bulk payload was already a complete framed message. The core ALSO supports fragmentation and concatenation for future use.
- TX (host to HRI): M10 (1), R6423 (1), P010000 (213), D1V0000 (142).
- RX (HRI to host): M10 (1), a variable identity-bearing R0 (1, always redacted), observed response B0 0    0000000 (213).
- Serial CDC setup on Windows: 38400 baud, 8N1. DTR+RTS were asserted by official software during initial setup. **This does not authorize repeating those actions on the physical adapter.**
- Observed P/B pairs (FIFO timing only) 213/213: 0.697–1.148 ms; 0.793 ms mean.
- D1V0000 occurred 142 times. Meaning still unknown; do NOT infer audio, PTT, COR, or a connection/room action from its name.
- The separate USB device 26AA:0003 exposes USB Audio and HID. The 0x01/0x04 frames are CDC signaling, not proof of an audio payload.

The Raspberry Pi 4 detected both HRI devices with lsusb, and the CDC port via udev was /dev/ttyACM0 using cdc_acm. **That path is a temporary OS assignment**, not a fixed runtime default; it must be rediscovered by VID/PID, interface and device ancestry.

## Original modules added

- core/hri200_protocol.py — pure in-memory incremental stream parser and passive session observer. Per-direction bounded buffers; resync on unexpected 0x01; frame classification only; FIFO P/B timing. Event objects omit payload bytes by design.
- tools/hri200_replay.py — reads an existing private local USBPcap recording, selects its address with --device, passes observed bulk bytes and timestamps to the core, prints aggregate privacy-safe JSON. Never opens USB/serial/audio/network interfaces.
- tests/test_hri200_protocol.py — synthetic fragmentation, concatenation, oversize, resynchronization, unknown payload, R0 redaction and timings.
- tests/test_hri200_replay.py — synthetic PCAP integration; checks that the capture-specific USB address is not hardcoded.

## Offline Windows test

Run from the repository root (PowerShell):

    py -3 tools/hri200_replay.py "$env:TEMP\HRI200_serial_test.pcap" --device 7

Address 7 was specific to the operator's private Windows recording; not an HRI-200 identity or Linux serial setting. The capture stays on the operator's Windows computer. **Never publish the raw PCAP, full R0 reply, station identities, passwords or tokens.**

## Portable offline checks on Debian / Raspberry Pi

    python3 -m unittest discover -s tests -v

Python 3.10+ standard library only; no installs, root privilege, hardware activity, or daemon restarts. A future mock transport may reuse this parser with captured, safely redacted fixtures.

## What is NOT implemented

- Opening, initializing, writing to, or reading from the *live* serial interface.
- Audio input/output, PTT/COR, RF control, USB HID commands.
- YAESU WIRES-X worldwide network protocol, authorized sign-in, listing rooms/nodes, joining rooms or forwarding digital voice.
- BrandMeister bridging. BM/XLX/TETRA configuration and services must remain untouched.

## Next engineering checkpoints

1. Obtain a clean Raspberry offline test run on the core. Check discovery result again only if the device changes.
2. Design a **separate disabled-by-default hardware transport** with explicit permission gates, a mock backend first and safe rollback; avoid implicit DTR/RTS changes and serial port contention. Opening a CDC port can have control-line side effects.
3. Independently study authorized YAESU network/room signaling. Hardware framing alone cannot establish a WIRES-X connection. Do not guess commands.
4. The existing BrandMeister-side operators independently connect to the owner's WIRES-X room; a direct native BrandMeister bridge is **not required** for the initial Linux room milestone. Do not touch operational BM, XLX or TETRA services.

## Windows USBPcap transfer/timing follow-up (2026-10-17)

The operator re-examined a private locally held Windows HRI-200 USBPcap using **offline, read-only** PowerShell. The report includes only aggregates, without USB payloads, identities or station data.

| USB endpoint | Transfer type | USBPcap records | With captured data | With no captured data |
| --- | --- | ---: | ---: | ---: |
| 0x01 | Bulk, PC to adapter | 714 | 357 | 357 |
| 0x82 | Bulk, adapter to PC | 431 | 215 | 216 |
| 0x00 and 0x80 | Control | 18 combined | Not categorized | Not categorized |
| 0x83 | Interrupt | 1 | 0 | 1 |

The complete file holds **1,164 USBPcap records**. The **572 bulk records with captured data** correspond to 357 host→HRI and 215 HRI→host application frames. Empty records may be submission/completion records and are **not proof of empty application messages**. The lone 0x83 interrupt record contains **zero captured payload bytes**; it is not evidence of a CDC SERIAL_STATE indication, USB HID message, PTT, COR or RF status. The captured USB address is capture-local and must not be configured as a default.

**Timing measured from recorded PC→adapter frames** (not an instruction to send them):

| Observed frame label | Samples | Min consecutive interval | Mean consecutive interval | Max consecutive interval |
| --- | ---: | ---: | ---: | ---: |
| `P010000` | 213 | 986.8 ms | 1,003.6 ms | 1,043.7 ms |
| `D1V0000` | 142 | 984.8 ms | 1,500.1 ms | 2,035.7 ms |

For the 141 gaps between `D1V0000` frames, **71 rounded to 1 second** and **70 rounded to 2 seconds**; the full rounded sequence had **140 of 140 possible alternations** (first 20: 1,2 repeated). This is consistent with two messages per three-second interval in this single Windows run, **not an identified command meaning or a tested Linux scheduler**.

A nearest-earlier-`P010000` comparison for 142 `D1V0000` frames produced offsets of **394.5–668.3 ms**, mean **586.8 ms**. Group counts by 50-ms offset bin: 350–399: 1; 400–449: 8; 450–499: 10; 500–549: 9; 550–599: 36; 600–649: 66; 650–699: 12. These offsets vary; do not claim a guaranteed fixed delay.

**Remaining unknown:** `D1V0000` semantics and its relation, if any, to audio, radio control or room state. Do **not** enable periodic hardware writes merely because cadence is observed. The `26AA:0003` composite audio/HID device is separate and its application traffic is **not validated** by this CDC-focused capture.

Source: IU0NDT's consent-based offline measurements (2026-10-15 and 2026-10-17). No proprietary executable or private capture in this repository.
