# YAESU WIRES-X worldwide protocol — verified research boundaries

**2026-10-15. Status:** research only. Native Linux HRI-200 **local USB CDC signaling is verified**; standalone native Linux **YAESU worldwide service authentication, room discovery, media and routing are not implemented**.

## What is firmly known

1. Owner confirmed native Raspberry Linux exchanges with a physically isolated HRI-200 USB serial 26aa:0002 (CDC ACM, 38400 8N1):
   - M10 -> M10 (5 TX / 5 RX)
   - R6423 -> R0 (7 TX / 74 RX, identity redacted)
   - P010000 -> B0 (9 TX / 17 RX)
   These are hardware exchanges. They do **not** show a WIRES-X account/server login.
2. WIRES-X is a YAESU-operated network of authorized registered nodes, list server, and rooms. Its application and network layer is separate from the local HRI-200 serial protocol and from YSF/FCS reflector protocols.
3. Legacy WIRES-X HRI-200 manuals list UDP 46100, 46110, 46112, 46114, 46120 and 46122 and describe WIRES ID activation/registration. **Do not treat these as mandatory ports for every current 2.0xx node.**
4. **Current YAESU documentation for software 2.0xx explicitly says that forwarding a port and obtaining a public IPv4 address is generally unnecessary for ordinary HRI-200 nodes.** The special case is a room that permits older nodes (1.570 or earlier): for that *legacy-compatible room*, YAESU specifies a public address and UDP 46114, 46120, 46122. A current 2.0xx installation may have different session/network behavior from the older 1.xxx reference documentation.
5. YAESU WIRES-X and WiRES-II are not interchangeable services. Both official reference manuals describe exporting a settings backup using extension `.wsv`, so **the extension alone does not establish which generation exported a file**.
6. A private user-provided text rendition of configuration data begins with `WIRES 3.600     SETTING`, has a size of 13,737 bytes in the supplied text rendition, and includes control characters. **We have not established whether "3.600" is a file-format version, product version, or something else, nor verified original binary fidelity.** Do not infer WiRES-II or WIRES-X provenance from this alone; inspect file origin using the owner's copy when possible. This document contains no file payload or embedded identities.

## Original references

- YAESU, current WIRES-X node matrix (version 2.000+ and legacy-compatible room exception): https://www.yaesu.com/jp/en/wires-x/node/index.php
- YAESU, earlier official HRI-200 instruction manual (older six-UDP-port configuration, activation and .wsv export): https://www.yaesu.com/jp/en/wires-x/contact/pdf/WIRES-X_Manual_ENG_1606-E0.pdf
- WIRES-X 2.010 May 2026 update notes mirrored with original Yaesu source linked: https://radio.xreflector.es/index.php/2026/05/01/wires-x-pc-software-ver-2-010-5-2026/
- YAESU WiRES-II 3.510 revision history (shows separately versioned older system): https://www.yaesu.com/jp/en/wiresinfo-en/new/120202.html
- WiRES-II reference manual, describes a .wsv backup format too: https://manualzz.com/doc/23472595/yaesu-wires-ii-wide-coverage-internet-repeater-enhancemen...
- K9EQ presentation about Fusion/WIRES-X architecture; background only, NOT a current wire protocol specification: https://files.tapr.org/meetings/DCC_2017/DCC2017-Fusion_from_the_Inside_Chris_Petersen_K9EQ.pdf

## Windows network trace evidence (2026-10-16)

The operator has now collected actual **network-header metadata** (not a server protocol implementation) from the original Windows WIRES-X application, with the radio disconnected. See [the redacted capture analysis](WIRESX_WINDOWS_NETWORK_EVIDENCE_2026-10-16.md) for the measured IPv4 UDP port/direction counts, anonymous peer patterns, message lengths and 10-second timelines.

**Verified:** local UDP 46100 (RX 74, TX 90) and UDP 46122 (RX 64, TX 43) were active; 46122 often received 31-byte UDP datagrams and transmitted 44-byte datagrams, while 46100 often transmitted 139-byte datagrams. **Unknown:** exact messages, which peer is YAESU vs BrandMeister, login sequence and room activation. Limited 54-byte packet prefix prevents application-payload interpretation. The user's existing room is connected **from BrandMeister's side**, so a direct BM adapter is out of scope for the initial native Linux WIRES-X room milestone.

## What remains UNKNOWN — no fictional protocol claims

- Server names/IP discovery, session sequence, authenticating against the current Yaesu service (including server-issued proof), refresh/reconnect behavior.
- Actual on-wire 2.010 packet fields, cryptography, message integrity and versions. UDP port numbers alone are not an application protocol.
- Live room discovery, joining/leaving, voice framing, codec, latency and routing semantics.
- Behavior and authenticity of bytes within the supplied private settings paste.
- Any approved method to act as a Linux native client using authorized registration and respecting Yaesu service terms.

## Safest evidence-gathering path: Windows original client only

The **genuine activated Windows WIRES-X 2.010** is the canonical source for authorized observation (the USBPcap file collected earlier captures only local USB traffic, not server packets). Begin with a **read-only inventory** of the TCP/UDP local ports associated with the legitimate WIRES-X process while it is running normally. Capture no payloads and publish no IP addresses, node IDs, callsigns or credentials.

Example: Windows PowerShell, without elevation, under an operator who controls the PC:

    Get-Process | Where-Object { $_.ProcessName -match 'wires' } | Select-Object ProcessName,Id

Only after verifying the real process name/PID, collect **redacted process-bound network metadata**, and consider an operator-approved, time-bounded local PCAP capture of the startup/room-list sequence **without RF activity**. Do not publish raw network PCAP files: activation tokens, station identifiers and IP addresses may be sensitive. Do not send custom network requests to YAESU servers, alter the activation registry, replay authorization tokens, or modify production network settings.

## Next engineering checkpoints

1. Correlate the legitimate Windows process with current TCP/UDP sockets, making no configuration changes.
2. Analyze a short authorized startup capture locally (only metadata first), distinguish DNS/bootstrap/list server and room media without making assumptions about control codes.
3. Document an independently testable, synthetic offline session model only once actual request/reply evidence supports it.
4. Validate permission/terms of service and user-owned activation before any interactive custom network client.
5. Keep BrandMeister, XLX, TETRA and all transmitters isolated until separately approved and certified.
