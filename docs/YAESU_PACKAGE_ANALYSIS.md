# Supplied YAESU package inventory — 2026-10-13

## Method and limits

The three user-supplied vendor ZIP files were examined **offline**, using
Python's ZIP reader for member names, sizes and dates plus SHA-256 for the ZIPs.
The executables, MSI, DLLs and firmware updater were **not run** and were not
published to GitHub. ZIP metadata timestamps do not specify a timezone.

| Supplied ZIP | SHA-256 (whole ZIP) | Contents / purpose |
| --- | --- | --- |
| `wx2010en.zip` | `b07acf93614f60bd306bc3f904642072e303265e14aa0b0456836da1a28de78c` | WIRES-X 2.010 Windows installer, YAESU HRI-200 serial INF, manuals |
| `wiresmon-x2000en.zip` | `cdef45ba4c0502c6ff90b09b32d47812d417fc4ca63eb22dbddd99393833363a` | WIRESMON-X remote monitor 2.000, support DLLs and documentation |
| `HRI-200_ver101(ENG).zip` | `723a24ee934b141de97c57a4c7aeb3f9e3a47b5b74857105d6fa5e0d003175f6` | HRI-200 firmware 1.01 update program and legacy runtime DLLs |

These hashes identify exactly the files the operator supplied; they are not
independent cryptographic attestations of YAESU provenance.

## WIRES-X 2.010 archive

- `en-US/WiresSetup.msi`: 22,380,544 bytes, modified 2026-04-28 according to ZIP header.
- `HRI-200_CommClass.inf`: YAESU Windows USB serial installer metadata.
- `HRI-200_Manual_ENG_2603-Q.pdf`, `WIRES-X_PDN_Function_OM_ENG_2603-N.pdf`: manuals.
- `Install.exe`, `SetupMenu32.exe`, `SetupMenu64.exe`: installers/launchers (not executed).

**Static INF facts:** Port A `USB\VID_26AA&PID_0002`;
Port B `USB\VID_26AA&PID_0005`; Port C
`USB\VID_26AA&PID_0008`. They use Windows `usbser.sys`.
The presence of these IDs **does not** prove that all three devices are
present on a particular PC or that a Linux driver is already validated.

## WIRESMON-X 2.000 archive

Five members: `WIRESMON-X.exe`, `DlgComFuncs.dll`,
`UdpComFuncs.dll`, `WIRESMON-X.chm`, `WIRESMON-X.txt`.

The vendor text describes remotely monitoring node identity, current
connections, RX/TX state and audio; it also describes specific remote control
capabilities, conditioned on the WIRES-X node's remote-monitor configuration.
It mentions the optional Web monitor backed by `WiresWeb.dll`.

**Important:** The filename `UdpComFuncs.dll` alone is not a network
protocol specification. The documented remote monitoring service may include
vendor-side authentication and infrastructure; this does not authorize
independent network control or establish a usable Linux API.

## HRI-200 firmware 1.01 archive

Contains the updater application, Windows runtime DLLs, driver helper and
firmware update guide. Do not run its updater during protocol research; a
firmware change would introduce a second variable and can disrupt a working
node.

## Engineering consequences

1. Keep original ZIPs outside Git, and never redistribute proprietary
   programs, DLLs or firmware.
2. Start with read-only enumeration of Windows PnP versus Raspberry Pi sysfs.
3. Treat USB CDC serial, USB audio and HID as separate functional interfaces.
4. Do not assume that serial framing or WIRES-X service authentication is
   documented merely because the port is CDC-like.
5. Use `tools/archive_inventory.py` for repeatable metadata-only checks
   and attach **sanitized results**, not vendor binaries, to issues.
