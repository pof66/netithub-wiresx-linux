# Portable Raspberry Pi packaging and self-extracting installer — DESIGN ONLY

**Status (2026-10-17):** architecture and acceptance criteria. **No installer has been built, certified, run, or released.** No functional Linux client for YAESU worldwide login or room operation exists yet.

## Goals and constraints

- Reusable NET.IT.HUB WIRES-X components for Raspberry Pi systems: device discovery, offline HRI-200 protocol analysis, optional future network client, isolated per-node configuration and room identity.
- **No hardware, station, network or deployment-specific constants in executable behavior**: no fixed /dev/ttyACM*, COM*, bus/address, station/room IDs, IP, DNS, callsign, path, USB device ordinal, Git remote/branch or secret in code or archive. Known YAESU VID/PID may be discovery signatures; the selection of a particular physical unit must be unambiguous.
- Every node/room instance uses its own explicit, validated config and state directory. A **one-room-per-WIRES-X-node assumption** is the conservative default until independently validated against the official service; multiple configured instances are not the same as unrestricted simultaneous multiple rooms.
- BrandMeister staff/servers **connect to the owner's WIRES-X room from their side**. Do not build a direct BM adapter into this initial installer or modify existing BM/XLX/TETRA.
- No automatic polling/writes on the HRI, CDC DTR/RTS changes, HID access, USB audio start, PTT/RF, service start, or network login just because a package is installed. **RF OFF by default.**
- No activation credentials, HRI identities, private ETLs, USBPcap recordings, IPs, MACs or opaque application bytes in public bundles, tests or GitHub.

## Raspberry Pi support matrix: test, do not promise universal support

- Runtime capabilities must be probed, not inferred from a marketing model name. Candidates include 32-bit armv6/armv7 and 64-bit aarch64, depending on Raspberry Pi model, distribution and kernel; exact support requires test results per combination.
- Python 3.10+ is the project's current standard-library baseline. Older Raspberry Pi OS images may lack it; installer **must stop with a clear message** instead of modifying Python or the OS in place.
- Detect OS, `uname -m`, Python version, filesystem permissions, libc/toolchain need if any, `cdc_acm` device availability and disk space. Never assume systemd is present or active.
- Test an explicit support matrix on real compatible hardware or reproducible images before saying “all Raspberry Pi”; older boards/OS versions could remain unsupported.

## Proposed bundle format

- A POSIX shell self-extracting wrapper containing a manifest and a compressed, read-only payload of project-owned files only.
- Manifest includes project/version/build revision, file checksums, supported Python/runtime range, target architecture requirements and a reproducible list of files.
- Extract to a temporary directory only after validation and archive path-traversal checks. Verify checksums and archive integrity **before** copying files. Never execute extracted scripts implicitly.
- Support explicit `--help`, `--inspect`, `--dry-run`, `--extract-to PATH`; installation is a **separate explicit `--install` action**, guarded by permission and destination checks. No `curl | sh` requirement.
- Configuration templates contain placeholders only, with secrets supplied at runtime through protected local configuration or environment, never embedded in the binary.
- Require an explicit destination prefix. Use versioned release directories with atomic switch and rollback plan. Back up config without overwriting existing instances.
- Do not assume one permanent root path or a GitHub branch. Release is an immutable artifact with checksums; optional upgrades must resolve the actual configured source and upstream dynamically, and refuse dirty/divergent checkouts.
- No package manager operations, systemd enable/reload/restart, user/group creation, network calls or RF service activation as installation side effects. Later, separately approved actions should each have their own visible flag and reversible plan.

## Candidate configuration schema (concept, not yet implemented)

```yaml
instance: <local-instance-name>
node:
  registered_id: <configured-station-id>
  callsign: <configured-callsign>
  hardware_mode: disabled
room:
  identity: <configured-room-id>
  enabled: false
hri:
  vendor_product_discovery: true
  selected_device: <explicit-selection-if-ambiguous>
  allow_live_io: false
network:
  allow_yaesu_worldwide_login: false
rf:
  enabled: false
paths:
  state_dir: <configured-state-directory>
```

This is illustrative documentation only: the repository does not currently parse this YAML. A configuration format should be chosen based on existing project dependencies and test coverage rather than introducing an unnecessary parser.

## Gates before a real release

1. Confirm the Windows HRI-200 CDC behavior and distinguish it from HID/audio; retain only sanitized observations.
2. Pass synthetic offline tests for framing, transport errors, device ambiguity, config validation and secure extraction (including path traversal and checksum mismatch).
3. Verify native Raspberry offline discovery on representative OS and CPU architectures, including an actual older 32-bit system if claimed supported.
4. Separately demonstrate a permitted YAESU worldwide authenticated connection and documented room behavior before claiming a working WIRES-X installer.
5. Validate dry-run/inspect, rollback, non-root paths, multiple instance isolation and fail-closed flags.
6. Operator explicitly approves each installation, daemon change, connection attempt, use of live HRI hardware or RF enabling. Without that approval, **no change to running infrastructure**.

**Engineering milestone:** design first; source and synthetic tests second; private staging third; release only on measured compatibility and authorization.
