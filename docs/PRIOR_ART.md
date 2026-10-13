# Prior art and feasibility review — 2026-10-13

## Scope and language

This is an independent **technical feasibility survey**, not a functional-compatibility claim. Distinguish the *radio-side "WIRES-X commands"* offered by some YSF gateway programs from the **YAESU WIRES-X service** with YAESU's own node/room ecosystem.

| Project / approach | Linux / Raspberry Pi | Connects natively to proprietary YAESU WIRES-X room network? | What we can study |
| --- | --- | --- | --- |
| G4KLX YSFClients / YSFGateway | Yes, 32/64-bit Linux supported | **No** — YSF/FCS reflector gateways | C4FM radio-side WIRES-X commands, modular configuration, reflector browsing |
| G4KLX DGIdGateway | Yes | **No** | DG-ID routes and network adapter architecture |
| WPSD / Pi-Star | Yes | **No**, standalone YSF/FCS gateways | Portable Raspberry deployment, monitoring, MMDVM ecosystem |
| YSF2DMR | Yes | **No** | Mode bridge, codecs, metadata translation |
| HRI-200 ↔ AllStarLink audio/PTT/COR | Raspberry can handle ASL side; YAESU PC remains in service | **Indirectly**, original WIRES-X software and hardware remain necessary | Separate control lines, analog signal paths, RX/TX interlocks |
| YAESU WIRES-X under Wine | Partial Linux experiments reported | **Experimental only**; short successful connection followed by crash | User-mode dependencies, serial support, audio/network problems |
| YAESU WIRES-X in Windows VM on Linux x86 host | Reported by operator | Works for reported operator, but is **not native Linux** | Baseline observation, test harness (not ARM-native client) |
| Independent HRI-200 / WIRES-X Linux client | Not found as a verified, complete open-source replacement in this survey | **Unknown / unproven** | Our main research question |

## Independent evidence

### YAESU support scope

YAESU's official "Opening a node" guide describes full-node operation with HRI-200 (including room creation, analog and digital operation), and lists Windows 11 and WIRES-X 2.x requirements. Portable Digital Node has additional restrictions; these configurations must not be conflated.

https://www.yaesu.com/jp/en/wires-x/node/index.php

YAESU's official HRI-200 listing also shows an archived PC software **1.570en** download in some regions, alongside **2.010**. Availability may vary by locale/login.

https://www.yaesu.com/product-detail.aspx?CatName=WIRESInternetLinking&Model=HRI-200

### G4KLX YSFClients

Official repository describes the Linux builds and use of radio-side WIRES-X commands for navigation of YSF reflectors. Does **not** establish entry to proprietary YAESU WIRES-X nodes or rooms.

https://github.com/g4klx/YSFClients

https://github.com/g4klx/YSFClients/blob/master/YSFGateway/YSFGateway.ini

### Wine / VM proof of partial operation

WineHQ discussion dated 2025-12-27 / 2026-02-25:

- WIRES-X v1.560 starts under Wine 11.0-rc4; a YAESU USB serial port maps to a Linux device, but YAESU network connectivity fails for the first experimenter.
- Another operator reports `winetricks`/WinINet enabled room listing and connection; incoming audio causes a crash.
- Report mentions a working setup in a Windows 11 VM under Linux on an x86 server, **not** Raspberry Pi native operation.

https://forum.winehq.org/viewtopic.php?t=42136

These are community reports, **not an endorsed or reproducible Raspberry Pi solution**.

### AllStarLink practical bridges

2024 and June 2026 forum reports describe hardware coupling of YAESU HRI-200 to AllStarLink via an audio/PTT/COR interface; interoperability is limited to analog/mixed configurations and attached equipment. More elaborate RF/MMDVM ↔ YSF ↔ DVSwitch pathways are also discussed.

https://community.allstarlink.org/t/yaesu-hri-200-to-allstar/22005

https://community.allstarlink.org/t/build-allstar-bridge-to-yaesu-wiresx-room/24676

https://www.usham.net/wiresx.html

### WPSD and YSF2DMR

https://wpsd.radio/

https://github.com/ea5gvk/YSF2DMR

## Observed HRI-200 device data (read-only Windows check)

Date: 2026-10-13. Windows reported all enumerated devices `OK`.

- `26AA:0002` — Communication device A (`COM21` on this particular Windows host), service `usbser`; compatible ID includes CDC ACM-style class/subclass/protocol.
- `26AA:0003` — Composite device; USB audio interface MI_00 and HID MI_03.

The host-generated serial suffixes and Windows COM number are **not portable** and must not be copied into runtime defaults. Confirmation of Linux driver binding, endpoint layout, buffering, baud/handshake expectations, serial command framing, audio paths, and HID semantics remains outstanding.

## What still needs proof

1. Can a stock Debian/Raspberry Pi kernel enumerate the HRI-200's CDC, audio and HID functions using mainline drivers? Which interface-specific quirks are needed?
2. Can we determine sufficient, permissible HRI-200 control exchanges to use it safely from independently authored software?
3. Is there a documented or otherwise authorized means for independently authored software to register/connect to the **original YAESU WIRES-X service**? No bypass of activation, authentication or entitlements is permitted.
4. Does WIRES-X 2.010 function better than 1.560 on Wine/WinINet, especially on audio receive? A Raspberry Pi/ARM compatibility claim would require additional work due to executable architecture.
5. Are media and signaling pathways available without RF or an external dedicated transceiver? They must not be assumed from USB enumeration alone.

## Research boundaries

- No vendor executable/DLL/firmware uploaded to source control.
- No publishing network authentication tokens, node secrets, private packet captures, or operator IDs.
- No installing Wine/USB drivers, service creation, udev changes, restarts, firmware update, network registration or RF TX as a side effect of research.
- No source copying or license-incompatible incorporation of existing GPL programs without clear licensing and attribution.
- Protocol work must comply with applicable law and service terms; keep tests consent-based and isolated.

## Proposed near-term next step

Perform **read-only, descriptor-only** USB identification on a Raspberry Pi test bench. Initial lab scripts should show a descriptive report and exit; they must never open/write to hardware interfaces or transmit RF in their default mode. Then use anonymized, consent-based observations of an already-running Windows node to define a mock-driven hardware abstraction layer.
