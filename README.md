# NET.IT.HUB WIRES-X Linux (research project)

**Status: research / no functional WIRES-X Linux client yet.**

Independent, portable Linux/Raspberry Pi research project for interoperating with YAESU HRI-200 hardware and investigating a native WIRES-X-compatible client. This project is **not affiliated with or endorsed by YAESU**.

## Critical distinction

- **YAESU WIRES-X**: proprietary network, node registration and room operation. A compatible independent Linux client has **not** been demonstrated here.
- **YSF / FCS / MMDVM**: separate open digital voice networking technologies. YSFGateway implements *radio-side WIRES-X-style commands* for reflector selection, **not** access to proprietary YAESU WIRES-X rooms.
- **Analog bridge**: HRI-200 + supported YAESU Windows software may be connected to AllStarLink through suitable audio/PTT/COR hardware. This is not a native replacement.

## Verified Windows lab observations (2026-10-13)

Read-only PowerShell device enumeration reported the following with OK status:

| Component | Windows device | USB identity | Windows service |
| --- | --- | --- | --- |
| HRI-200 Communication device A | COM21 | VID 26AA, PID 0002 | `usbser` |
| HRI-200 A (CH1) USB Audio codec | MEDIA | VID 26AA, PID 0003, MI 00 | `usbaudio` |
| USB composite device | USB | VID 26AA, PID 0003 | `usbccgp` |
| USB input HID | HIDClass | VID 26AA, PID 0003, MI 03 | `HidUsb` |
| HID consumer-control collection | HIDClass | VID 26AA, PID 0003, MI 03 | service not reported (PnP status OK) |

`USB\\Class_02&SubClass_02&Prot_01` is advertised among compatible IDs for PID 0002, consistent with a CDC ACM serial function. **Linux `cdc_acm`, `snd-usb-audio` and `usbhid` driver bindings are now verified on a Raspberry Pi 4.** No hardware writes, firmware updates, or RF transmissions were performed.

User-supplied reference archives examined preliminarily: `wx2010en.zip`, `HRI-200_ver101(ENG).zip`, `wiresmon-x2000en.zip`. **Do not commit, copy, or redistribute YAESU EXE/DLL/firmware or user secrets in this repository.**


## Physical Raspberry Pi 4 USB result (2026-10-13)

The operator connected a real HRI-200 to a Raspberry Pi 4 Linux host and obtained the following read-only evidence:

| USB device | Interface(s) | Kernel driver | USB speed |
| --- | --- | --- | --- |
| 26aa:0002 communication device A | 0 (Communications), 1 (CDC Data) | `cdc_acm` | 12 Mbit/s |
| 26aa:0003 audio/HID | 0, 1, 2 (Audio) | `snd-usb-audio` | 12 Mbit/s |
| 26aa:0003 audio/HID | 3 (HID) | `usbhid` | 12 Mbit/s |

**The kernel-side USB recognition milestone and first live Python discovery milestone have been achieved.** On Raspberry Pi 4 with Python 3.13.5, the actual [`tools/hri200_discovery.py`](tools/hri200_discovery.py) script identified the HRI-200's `26aa:0002` serial device and `26aa:0003` audio device and reported one serial and one audio candidate. These are read-only sysfs results; no serial session, PCM audio stream, HID report, RF transmission, proprietary network authentication or functional WIRES-X operation has been tested. See [USB test evidence](docs/USB_PROBE.md).

## HRI-200 HID descriptor research

A **read-only kernel HID report descriptor inspection** on Raspberry Pi 4 found a standard Consumer Control input report: 1-bit Volume Increment, Volume Decrement and Mute fields plus 5 padding bits (one byte, no Report ID). The descriptor does **not** declare PTT, COR/COS or WIRES-X room controls. This is a description of input fields, not proof of transmitted reports or of any radio control behavior. Do not attempt speculative HID control writes. See [USB/HID technical evidence](docs/USB_PROBE.md).

## Design requirements

- Native Linux on Raspberry Pi OS/Debian (ARM64/ARM32 where supportable) and Debian x86_64.
- Installation and uninstall procedures that are reproducible, idempotent, configurable, and non-destructive.
- Never hardcode local IPs, nodes, callsigns, USB port names, hostnames, directories, Git remotes, branches, reflectors or network routing values.
- Device selection by discovered stable identifiers, not Windows COM port numbers.
- Separate hardware transport, application behavior, protocol adapters and API/UI.
- Explicit **RF/TX disabled by default**; no unattended TX, firmware flashing, connection attempts, or service restarts.
- No bypass of operator registration, authentication, entitlements or other access controls.
- Never store credentials in Git; separate redacted captures and encrypted local secrets.
- Follow open-source license conditions for third-party components. Implement original code from public specifications and permissible interoperability research.

## Proposed logical layout (not implemented)

```text
hardware/       HRI-200 discovery, CDC/USB serial, ALSA, HID
core/           state, sessions, node/room domain models
protocols/      replaceable protocol and media adapters
bridge/         optional external radio-core / AllStar / SvxLink integration
web/            monitoring and configuration (later)
installer/      portable install/uninstall and prerequisites (later)
tests/          offline protocol and device-fake tests
docs/           research reports, contracts and design decisions
```

This tree is an architecture proposal, **not** a claim that any of these modules work today.

## Planned verification gates

1. **USB-only discovery on Linux:** VID/PID, configuration descriptors, interfaces, `cdc_acm`, ALSA, hidraw. Read-only.
2. **Hardware I/O:** reproduce only documented or safely observed control/telemetry exchanges in an isolated bench setup. TX must remain disabled.
3. **Network feasibility:** understand protocol and supported, authorized authentication requirements; assess if a native WIRES-X connection is technically and legally viable.
4. **Offline adapters and tests:** repeatable simulations and logs with anonymization; integration without specific deployment IDs.
5. **Installer:** only after functionality has been validated and user explicitly approves installation and service activation.

See [docs/PRIOR_ART.md](docs/PRIOR_ART.md) for researched software, references and open questions.

## Scope of contributions

Research reports, interoperability tests, mock devices, documentation and independent code are welcome. No YAESU executables, reverse-engineered secrets, credentials, private traffic or proprietary firmware may be submitted.

**This project does not yet have a working installer.** Do not treat this repository as an operational radio node.

## Local WIRES-X Last Heard dashboard (experimental)

The repository now contains an **original, read-only local monitor** for an existing WIRES-X `WiresAccess.log`:

- [Python parser and loopback JSON API](tools/wiresx_lastheard.py) — parses local Last Heard snapshots without any serial, audio, HRI-200, YAESU server or RF interaction.
- [Dashboard HTML](web/wiresx_monitor.html), [CSS](web/wiresx_monitor.css) and [JavaScript](web/wiresx_monitor.js) — Italian Last Heard table, year/channel summaries, privacy-aware position counts and 15-second refresh.
- [Synthetic privacy/parser tests](tests/test_wiresx_lastheard.py) and [full Windows/Linux usage guide](docs/LAST_HEARD_MONITOR.md).

**Private by default:** local 127.0.0.1 server only, ephemeral station aliases, no raw GPS, radio ID, or personal log content in the HTTP output. Callsigns require explicit opt-in. This monitor does **not** report live RX/TX, connect to YAESU's network, install services or control radios. The HTTP UI has not yet been verified on the operator's Windows machine. See the guide for commands and limitations.

## Diagnostics now in this repository

- [Windows HRI-200 PnP inventory](tools/windows/hri200_inventory.ps1) — read-only USB/driver snapshot, excludes full serial instance identifiers. See [instructions](docs/WINDOWS_INVENTORY.md).
- [Linux HRI-200 USB probe](tools/usb_probe.py) — sysfs-only detection, no hardware ports opened. See [instructions](docs/USB_PROBE.md).
- [Portable Linux endpoint discovery](tools/hri200_discovery.py) — matches CDC serial, ALSA audio and HIDRAW through their YAESU USB ancestors without opening device nodes; HID/audio matching uses the same USB `26aa:0003` parent and ambiguity between serial/audio devices requires operator selection. JSON schema `hri200-linux-discovery-v2`. Discovery V2 has now been executed successfully on a real Raspberry Pi 4 with Python 3.13.5, detecting CDC, ALSA and HIDRAW through sysfs (no streams/port opens). [Mock-backed tests](tests/test_hri200_discovery.py).
- [Offline vendor ZIP inventory](tools/archive_inventory.py) — bounded ZIP metadata inspection, file signatures and SHA-256 without extraction.
- [Supplied YAESU packages](docs/YAESU_PACKAGE_ANALYSIS.md) — checksum-anchored analysis of 2.010, remote monitor 2.000 and firmware 1.01 packages, with no proprietary files uploaded.
- [Offline test suite](tests) — synthetic fixtures. GitHub Actions definitions are in [offline-tests.yml](.github/workflows/offline-tests.yml); CI completion has not yet been independently verified.

**Warning:** None of these tools authenticates to YAESU, controls HRI-200, sends RF, or constitutes a working WIRES-X Linux client. The installer remains future work after a validated, permitted implementation exists.

## License and attribution

**Original project credit:** Copyright © 2026 **IU0NDT**.

The original code and documentation independently authored for this repository are distributed under the [Apache License, Version 2.0](LICENSE). The [NOTICE](NOTICE) identifies the original project and its source: [pof66/netithub-wiresx-linux](https://github.com/pof66/netithub-wiresx-linux).

Redistribution and derivative works must comply with the license, including preserving applicable copyright, license and attribution notices, and the relevant contents of `NOTICE` as described in Section 4. This is **not** a requirement to display IU0NDT in a program's splash screen or to obtain permission for every reuse. We welcome an explicit link to this repository when discussing or republishing derived material.

The license applies only to rights held in the independently created project material; it **does not license** YAESU software, firmware, documentation, names or trademarks, or any independently licensed third-party material. YAESU is not a sponsor or affiliate of this project.
