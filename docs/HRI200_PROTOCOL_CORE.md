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
4. Only after end-to-end test evidence and explicit approval, plan an isolated BM bridge with audio source/sink control and no changes to the existing operational BM environment.

Source: IU0NDT's consent-based offline measurements (2026-10-15). No proprietary executable or private capture in this repository.
