#!/usr/bin/env python3
# Copyright 2026 IU0NDT
# SPDX-License-Identifier: Apache-2.0
"""Read-only local WIRES-X WiresAccess.log snapshot and dashboard API.

No HRI-200, YAESU network, RF control, writes to the log, or dependencies.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import secrets
import sys

GPS = re.compile(
    r'^([NS]):(\d{1,2}) (\d{2})\' (\d{2})" / ([EW]):(\d{1,3}) (\d{2})\' (\d{2})"$'
)
WEB_ROOT = Path(__file__).resolve().parent.parent / "web"
MAX_ROWS = 500


def valid_coordinates(text: str) -> bool:
    """Validate format and ranges, but never publish the coordinates."""
    match = GPS.fullmatch(text.strip())
    if match is None:
        return False
    _, lat, lm, ls, _, lon, om, os = match.groups()
    lat_d, lon_d = int(lat), int(lon)
    if not (lat_d <= 90 and lon_d <= 180):
        return False
    if not all(0 <= int(x) < 60 for x in (lm, ls, om, os)):
        return False
    if lat_d == 90 and (int(lm) or int(ls)):
        return False
    if lon_d == 180 and (int(om) or int(os)):
        return False
    return True


def parse_log(path: Path, *, secret: bytes, show_callsigns: bool = False,
              limit: int = MAX_ROWS) -> dict:
    """Return JSON-safe Last Heard snapshot; never expose IDs or GPS coordinates."""
    counts = Counter()
    channels = Counter()
    rows = []
    with Path(path).open("r", encoding="utf-8-sig", errors="replace") as src:
        for line in src:
            if not line.strip():
                continue
            counts["total_rows"] += 1
            fields = line.rstrip("\r\n").split("%")
            if len(fields) < 8:
                counts["malformed_rows"] += 1
                continue
            try:
                when = datetime.strptime(fields[3].strip(), "%Y/%m/%d %H:%M:%S")
            except ValueError:
                counts["invalid_dates"] += 1
                continue
            counts["parsed_rows"] += 1
            counts["year_" + str(when.year)] += 1
            if when.year == 2000:
                counts["year_2000_candidate_placeholder"] += 1
            else:
                counts["other_dated_rows"] += 1
            position = valid_coordinates(fields[6])
            if position:
                counts["records_with_valid_coordinates"] += 1
            channel = fields[4].strip()[:32] or "UNKNOWN"
            channels[channel] += 1
            private_identity = "\x1f".join((fields[0], fields[1], fields[2])).encode(
                "utf-8", errors="replace"
            )
            alias = "ST-" + hmac.new(secret, private_identity, hashlib.sha256).hexdigest()[:10].upper()
            callsign = fields[2].strip()[:32]
            rows.append({
                "station": callsign if show_callsigns and callsign else alias,
                "received": when.isoformat(sep=" "),
                "year": when.year,
                "channel": channel,
                "has_position": position,
                "date_placeholder": when.year == 2000,
            })

    rows.sort(key=lambda x: x["received"], reverse=True)
    dated = [r["received"] for r in rows if not r["date_placeholder"]]
    years = {
        year[5:]: n for year, n in sorted(counts.items()) if year.startswith("year_")
        and year[5:].isdigit()
    }
    return {
        "schema": "netithub-wiresx-lastheard-v1",
        "source": "WIRES-X WiresAccess.log (read-only snapshot)",
        "live_rx_tx": False,
        "identifiers_visible": show_callsigns,
        "summary": {
            "total_rows": counts["total_rows"],
            "parsed_rows": counts["parsed_rows"],
            "malformed_rows": counts["malformed_rows"],
            "invalid_dates": counts["invalid_dates"],
            "year_2000_candidate_placeholder": counts["year_2000_candidate_placeholder"],
            "other_dated_rows": counts["other_dated_rows"],
            "records_with_valid_coordinates": counts["records_with_valid_coordinates"],
            "latest_non_2000_received": max(dated) if dated else None,
            "years": years,
            "receive_channels": dict(sorted(channels.items())),
        },
        "rows": rows[:limit],
        "truncated": len(rows) > limit,
    }


def dashboard_handler(log_path: Path, show_callsigns: bool, secret: bytes):
    """Create a local HTTP handler without write routes."""
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            # Avoid recording request metadata on disk or the console.
            pass

        def respond(self, status: int, body: bytes, kind: str):
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'none'; style-src 'self'; script-src 'self'; "
                "connect-src 'self'; img-src 'self'; base-uri 'none'; frame-ancestors 'none'",
            )
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            # Block DNS rebinding; server itself binds only to loopback.
            host = self.headers.get("Host", "")
            if host.split(":")[0].lower() not in ("localhost", "127.0.0.1"):
                return self.respond(403, b"Forbidden", "text/plain; charset=utf-8")
            route = self.path.split("?", 1)[0]
            if route == "/api/lastheard":
                try:
                    data = parse_log(log_path, secret=secret, show_callsigns=show_callsigns)
                    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
                except OSError:
                    return self.respond(503, b'{"error":"Log currently unavailable"}', "application/json")
                return self.respond(200, body, "application/json; charset=utf-8")
            resources = {
                "/": ("wiresx_monitor.html", "text/html; charset=utf-8"),
                "/wiresx_monitor.css": ("wiresx_monitor.css", "text/css; charset=utf-8"),
                "/wiresx_monitor.js": ("wiresx_monitor.js", "text/javascript; charset=utf-8"),
            }
            if route not in resources:
                return self.respond(404, b"Not found", "text/plain; charset=utf-8")
            name, kind = resources[route]
            try:
                body = (WEB_ROOT / name).read_bytes()
            except OSError:
                return self.respond(503, b"Dashboard assets unavailable", "text/plain")
            return self.respond(200, body, kind)

    return Handler


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--log", type=Path, required=True, help="Path to local WiresAccess.log")
    ap.add_argument("--serve", action="store_true", help="Start loopback-only dashboard")
    ap.add_argument("--port", type=int, default=8765, help="Local HTTP port (default: 8765)")
    ap.add_argument("--show-callsigns", action="store_true",
                    help="Explicit opt-in: show callsigns on THIS COMPUTER only")
    args = ap.parse_args(argv)
    if not args.log.is_file():
        ap.error("Log file not found (no files have been changed)")
    if not 1 <= args.port <= 65535:
        ap.error("--port must be 1..65535")
    secret = secrets.token_bytes(32)
    if args.serve:
        host = "127.0.0.1"  # Intentional security boundary: no remote listen option.
        handler = dashboard_handler(args.log, args.show_callsigns, secret)
        try:
            with ThreadingHTTPServer((host, args.port), handler) as httpd:
                print(f"NET.IT.HUB WIRES-X monitor: http://{host}:{args.port}/")
                print("Local-only; Ctrl+C to stop; no WIRES-X or RF access.")
                if args.show_callsigns:
                    print("CAUTION: callsigns visible in this computer's dashboard/API.")
                httpd.serve_forever(poll_interval=0.5)
        except KeyboardInterrupt:
            print("\nMonitor stopped.")
        except OSError as exc:
            print(f"Unable to start local monitor: {exc}", file=sys.stderr)
            return 2
        return 0
    try:
        data = parse_log(args.log, secret=secret, show_callsigns=args.show_callsigns)
    except OSError as exc:
        print(f"Unable to read log: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(data["summary"], indent=2, ensure_ascii=False))
    print("Snapshot only; RX/TX live not available from this log.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
