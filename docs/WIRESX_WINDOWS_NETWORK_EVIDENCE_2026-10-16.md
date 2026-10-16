# WIRES-X 2.010 network observation — Windows, 16 October 2026

**Status:** independently collected metadata from the operator's authorized original Windows application; **not a decoded YAESU application protocol** and **not a working Linux network client**.

The working HRI-200 CDC handshake on Linux is documented separately in [HRI200_LINUX_SESSION.md](HRI200_LINUX_SESSION.md). This report covers **Windows network traffic**, not USB or RF.

## Capture methodology and limitations

- Original Windows WIRES-X client observed running and bound to UDP ports 46100, 46110, 46112, 46114, 46120, 46122, 46130, 46132 and 46160; TCP port 46190 was in LISTEN state. These are **bound sockets**, not evidence of a network exchange on every listed port.
- Initial PktMon captures reported only 3 WMI events per file (approximately 14.7 KB): **no packet records for analysis**. Never infer a silent WIRES-X client from this failed capture method.
- A later 60-second `netsh trace` captured via the owner's actual physical Ethernet interface; `PacketTruncateBytes=54`, so the trace can support link/IP/UDP-header metadata but **not the complete application payload**.
- The resulting Windows trace was 4 MiB (allocation may affect file size), and its CSV event listing had 19,126 rows: 18,954 named Microsoft-Windows-NDIS-PacketCapture events, of which 18,946 were Event ID 1001.
- Offline local decoding yielded 18,219 IPv4 frame observations and 644 IPv6 frames not decoded by the script. Events may include network traffic **unrelated to WIRES-X**; matching port numbers alone do not prove process attribution.
- The ETW Event ID 1001 exposed `Properties[3].Value` as a `Byte[]` of 54 bytes. Direct access avoids costly full XML conversion for each event. CSV `User Data` did **not** contain the packet fragments.
- NIC ownership was classified from the locally known Ethernet MAC during offline analysis. **This document intentionally omits the MAC, interface GUID, IP addresses, account and node identifiers, private captures and packet contents.**

## Distinct WIRES-X-port local traffic on IPv4

These counts reflect packets **where the specified port belongs to the Windows client-side endpoint**, not both ends of a datagram. The operator's original port-grouping command that counted matches at either endpoint caused double/misleading attribution for 46110, 46112 and 46122.

| Local UDP port | RX packets | TX packets | Total | Observation |
| --- | ---: | ---: | ---: | --- |
| 46100 | 74 | 90 | 164 | Active bidirectional |
| 46110 | 1 | 0 | 1 | One inbound packet |
| 46112 | 1 | 1 | 2 | Sparse |
| 46114 | 1 | 0 | 1 | Sparse |
| 46120 | 1 | 0 | 1 | Sparse |
| 46122 | 64 | 43 | 107 | Active bidirectional |
| **All local ports above** | **142** | **134** | **276** | **Observed packets, not transactions** |

No *local-endpoint* exchange was detected at 46130, 46132, 46160 or TCP 46190 in this truncated IPv4 UDP-focused summary. Their lack of detected traffic **does not mean those ports are unused in other sessions**.

### Peer grouping (pseudonyms local to this single recording)

The same anonymous peer identifier was assigned to a unique remote IPv4 address **within this capture only**. The labels are not authoritative names or provider assignments.

| Peer | Local port and remote port | RX | TX |
| --- | --- | ---: | ---: |
| Peer-4 | 46100 / remote 49690 | 69 | 75 |
| Peer-2 | 46100 / remote 49690 | 3 | 9 |
| Peer-3 | multiple local ports; remote 46002 or 49690 | 7 | 7 |
| Peer-1 | 46122 / remote 46110 or 46112 | 63 | 43 |

**Unknown:** which peer is a YAESU server, another WIRES-X room or a BrandMeister-side endpoint. There is **no valid process-level or application-level classification yet**.

## Wire lengths (UDP datagram field, including 8-byte UDP header)

| Local port | Direction | Most prominent observed UDP length | Count |
| --- | --- | ---: | ---: |
| 46100 | TX | 139 bytes | 69 |
| 46100 | RX | many values approximately 1,021–1,262 bytes | usually 1 or 2 each |
| 46122 | RX | 31 bytes | 60 |
| 46122 | TX | 44 bytes | 38 |

These observations are **compatible with** differing application behaviors and periodic traffic; they do not establish which specific frames perform registration, room activation, keepalive or media.

## Changes over time (relative bins from first matching packet)

| Seconds | 46100 RX | 46100 TX | 46122 RX | 46122 TX |
| --- | ---: | ---: | ---: | ---: |
| 00–09 | 2 | 1 | 10 | 8 |
| 10–19 | 1 | 13 | 11 | 8 |
| 20–29 | 1 | 0 | 11 | 0 |
| 30–39 | 16 | 21 | 12 | 12 |
| 40–49 | 26 | 27 | 9 | 8 |
| 50–59 | 27 | 27 | 11 | 7 |
| 60–69 | 1 | 1 | 0 | 0 |

A small number of other local ports (46110, 46112, 46114, 46120) saw events in the 20–29 s bin. The first `TimeCreated` matching packet is the zero point; these bins **do not timestamp the exact GUI operations**. The owner reported closing/reopening WIRES-X, client reconnect, node/room lists reloaded and a BrandMeister connection to the owner's WIRES-X room during the test window. **Do not infer causal correspondence without instrumented operator timestamps.**

## Project scope clarified by the operator

1. Make an authorized, registered **native Linux WIRES-X** client that makes an operator-managed room available, without a radio or active RF/PTT.
2. The **BrandMeister operators connect to the owner's WIRES-X room on their side** and independently arrange its relationship to a DMR talkgroup. **No separate direct BrandMeister protocol/bridge implementation is required** for the initial Linux milestone; preserve their current connection and configuration.
3. No testing that alters existing BM, XLX, TETRA, PTT or radio services without explicit authorization.

## Next investigation

- A separate capture with a larger bounded prefix (256 bytes) was proposed but **not yet reported as completed** in this evidence set. Even 256 bytes might cut long application messages; never claim full protocol recovery from truncated data.
- Produce an original, privacy-preserving **offline Windows trace analyzer** with robust parsing, synthetic tests, no publication of capture bytes, IPs, credentials or opaque payloads, and no interaction with the service.
- Record precise **local** timestamps for the operator's GUI actions (client start, signed-in/online, room activation, room-list refresh, external peer connects/disconnects) and correlate them with frame directions and sizes without guessing protocol labels.
- Resolve the service's authorization and access contract before implementing any outbound native Linux network messages. No authentication replay, no reverse-engineered keys, no fabricated login sequence.
- No fresh capture, installation, Git history rewriting, restart, RF activity or service changes are part of this report.

**Sensitive data policy:** Never commit the private ETL, CAB, CSV, pcap, settings files, IDs, peer IPs, MACs, activation details, credentials or raw application messages.
