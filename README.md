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

**The kernel-side USB recognition milestone has been achieved** without installing a YAESU driver. No serial session, audio sample, HID exchange, RF, proprietary network authentication or functional WIRES-X operation has been tested. Next step: inspect the character device nodes using read-only commands. See [USB test evidence](docs/USB_PROBE.md).

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

## Diagnostics now in this repository

- [Windows HRI-200 PnP inventory](tools/windows/hri200_inventory.ps1) — read-only USB/driver snapshot, excludes full serial instance identifiers. See [instructions](docs/WINDOWS_INVENTORY.md).
- [Linux HRI-200 USB probe](tools/usb_probe.py) — sysfs-only detection, no hardware ports opened. See [instructions](docs/USB_PROBE.md).
- [Offline vendor ZIP inventory](tools/archive_inventory.py) — bounded ZIP metadata inspection, file signatures and SHA-256 without extraction.
- [Supplied YAESU packages](docs/YAESU_PACKAGE_ANALYSIS.md) — checksum-anchored analysis of 2.010, remote monitor 2.000 and firmware 1.01 packages, with no proprietary files uploaded.
- [Offline test suite](tests) — synthetic fixtures. GitHub Actions definitions are in [offline-tests.yml](.github/workflows/offline-tests.yml); CI completion has not yet been independently verified.

**Warning:** None of these tools authenticates to YAESU, controls HRI-200, sends RF, or constitutes a working WIRES-X Linux client. The installer remains future work after a validated, permitted implementation exists.
