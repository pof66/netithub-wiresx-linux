# NET.IT.HUB WIRES-X Linux — first physical CDC exchanges

**Milestone: 2026-10-15.** This is a physical HRI-200 serial interface milestone, **not** worldwide WIRES-X network connectivity and not a BrandMeister bridge.

## Verified on an RF-isolated Raspberry Pi

The owner individually tested three consent-based, single-shot exchanges with a physical HRI-200 over Linux CDC ACM at 38400 baud, 8N1. The HRI USB serial device identified as 26aa:0002 (temporary /dev/ttyACM0); USB audio was detected separately as 26aa:0003.

| Request from Raspberry | HRI-200 reply | TX bytes | RX bytes |
| --- | --- | ---: | ---: |
| M10 | M10 | 5 | 5 |
| R6423 | R0 (identity suppressed) | 7 | 74 |
| P010000 | B0 | 9 | 17 |

Messages were framed with 0x01 before the ASCII body and 0x04 after it. An initial passive RX-only test received 0 bytes in 3 seconds. The former Windows USBPcap capture had shown the same message classes; that did not establish their full semantics.

## New Linux modules

- hardware/hri200_cdc.py — exclusive, bounded, 38400 8N1 Linux CDC transport, limited to the three observed requests, with termios restoration and abort on unexpected replies.
- tools/hri200_session.py — default read-only discovery by USB identity, active run-once only behind two explicit flags.
- core/hri200_protocol.py — privacy-preserving incremental framing engine.
- tests/test_hri200_cdc.py — offline isolated synthetic replies plus Linux pseudo-terminal I/O test; no RF equipment required.

No D1V0000 commands, continuous polling, PTT actions, USB audio, HI D writes, network traffic or YAESU login are implemented. Messages returned from the adapter are classified without showing raw R0 identity or other private bytes.

## Run from the repository root on Linux

Read-only discovery, opens no serial port:

    python3 tools/hri200_session.py

**Explicit, single run on an HRI-200 physically isolated from radio/PTT, with RF disabled:**

    python3 tools/hri200_session.py --run-once --rf-isolated

Port assignment is resolved through sysfs VID/PID; /dev/ttyACM0 is NOT hardcoded. If more than one 26aa:0002 serial endpoint exists, select an observed one with --port. No service installation or restart.

**Warning:** Merely opening a Linux CDC ACM port can implicitly alter DTR/RTS. The driver does not explicitly set these control lines. Linux TIOCEXCL prevents new concurrent opens, but it cannot guarantee no pre-existing open handles. A hardware-free environment is mandatory for this phase.

## Future milestones

1. Confirm the *integrated* tool against the isolated Raspberry, as distinct from the three individually verified manual experiments.
2. Validate error handling, port disappearance and timing without transmitter connections.
3. Investigate authorized YAESU WIRES-X worldwide service protocol and authentication. These three CDC exchanges **do not connect** the Raspberry to YAESU worldwide rooms.
4. Design a separately approved and isolated BrandMeister integration only after original WIRES-X network and audio have been demonstrated and certified. No BM, XLX or TETRA changes now.

The public repository intentionally contains no original proprietary executables, private traffic captures, identity strings, credentials, or raw R0 responses.
