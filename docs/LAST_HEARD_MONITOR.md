# WIRES-X Last Heard local dashboard (experimental)

**Status 2026-10-15:** Original parser and local dashboard implemented. Four fully synthetic parser tests passed locally. The earlier stand-alone log reader was validated against the owner's Windows WIRES-X 2.010 log (240 records). The new HTTP dashboard still requires validation on the operator's Windows PC. This is neither an operational WIRES-X node nor a live RX/TX monitor.

## Source / semantics

Source: existing user-owned WIRES-X WiresAccess.log, from an explicit --log path. The tool never creates or alters a WIRES-X logfile or configuration.

One authorized local sample from 2026-10-15: 240 rows; zero malformed entries; six year-2000 dates (possible placeholders); 234 other dates; 48 valid position strings; 240 rows with Room as channel; latest non-2000 reception 2026-10-15 11:55:20.

Format: percent-separated fields. Existing independent research at https://github.com/adilinden-oss/wires-scripts/blob/master/wires2aprs.pl documents columns 1/2/3 as User ID, Radio ID, Callsign; 4 as date; 5 as receive channel; 7 as last position. Other columns are not confidently identified, and are not exported.

A row may represent the latest known reception for a station, **not each PTT**. A periodic browser refresh does not convert this file into a full event history.

## Architecture

- tools/wiresx_lastheard.py: standard-library read-only parser and local HTTP JSON API.
- web/wiresx_monitor.html: original Italian monitoring interface.
- web/wiresx_monitor.css: technical responsive styling.
- web/wiresx_monitor.js: polling every 15 seconds; renders untrusted fields only with textContent, not innerHTML.
- tests/test_wiresx_lastheard.py: fully synthetic parser and privacy checks.

GET /api/lastheard returns netithub-wiresx-lastheard-v1 JSON: summary counts, year/channel totals, and up to 500 rows (station, received, year, channel, has_position). It is a snapshot, not an RX/TX stream.

## Safety and privacy

- HTTP server binds only to 127.0.0.1; no option enables a public interface. Host header restriction mitigates DNS rebinding. Do not reverse-proxy the server publicly.
- By default station labels are HMAC pseudonyms with a random per-process secret. They may change when restarted.
- Raw GPS coordinates, User IDs, Radio IDs, encoded metadata, private log content and credentials are never returned.
- Optional --show-callsigns must be explicitly enabled and displays callsigns only on the local dashboard and JSON; it does not expose raw radio IDs or GPS. Do not enable on shared PCs.
- No HRI-200 communication, USB access, serial writes, audio streams, YAESU network login, installs, restarts, or RF transmissions.
- No public map. Exact locations require a separate access-control and consent review.

## Windows launch (Python 3.14)

Download or clone the repository preserving the tools/ and web/ folder layout. Run these PowerShell lines **from the repository root**:

    $log = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'WIRESXA\AccHistory\WiresAccess.log'
    py -3 .\tools\wiresx_lastheard.py --log $log --serve

Open http://127.0.0.1:8765/ on the same PC. Stop with Ctrl+C.

CLI summary only, no web server:

    py -3 .\tools\wiresx_lastheard.py --log $log

Optional opt-in to callsign visibility: append --show-callsigns to the serve command. Consider the privacy implications first.

## Debian / Raspberry Pi

    python3 tools/wiresx_lastheard.py --log /path/to/your/WiresAccess.log --serve --port 8765

The log must already be available at the path supplied by the operator. This tool does not acquire it from Windows, sync it, or install services. Browser access is local to the Linux host.

## Offline tests

    python3 -m unittest discover -s tests -p 'test_wiresx_lastheard.py' -v

## Next gates

1. Verify the new UI on the operator's real Windows sample, comparing counts with the previously validated stand-alone reader.
2. Investigate whether WIRES-X updates entries or appends event history before adding a true timeline.
3. Design a separately authenticated integration before any proposed remote hosting; the current API is loopback only.
4. Discover separate authorized data sources for actual live RX/TX, connected nodes, room activity, audio and metadata.
5. No unapproved TETRA, XLX, BrandMeister or RF changes.
