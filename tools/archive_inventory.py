#!/usr/bin/env python3
# Copyright 2026 IU0NDT
# SPDX-License-Identifier: Apache-2.0
# Source: https://github.com/pof66/netithub-wiresx-linux

"""Offline metadata-only inventory for vendor ZIP files.

No member is extracted or executed. This tool is not a disassembler or a
WIRES-X protocol decoder. It never uploads archive contents or connects to
a network. It uses only the Python standard library.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

CHUNK = 1024 * 1024
DEFAULT_MAX_MEMBER = 64 * 1024 * 1024
DEFAULT_MAX_TOTAL = 256 * 1024 * 1024


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as src:
        while chunk := src.read(CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def signature(header: bytes) -> str:
    if header.startswith(b"MZ"):
        return "PE/DOS executable header"
    if header.startswith(b"%PDF-"):
        return "PDF"
    if header.startswith(bytes.fromhex("d0cf11e0a1b11ae1")):
        return "OLE compound document (possible MSI)"
    if header.startswith(b"PK\x03\x04"):
        return "ZIP container"
    if header.startswith(b"MSCF"):
        return "CAB archive"
    return "unidentified"


def inventory(path: Path, max_member: int = DEFAULT_MAX_MEMBER,
              max_total: int = DEFAULT_MAX_TOTAL) -> dict:
    """Return metadata and hashes; impose decompression limits in advance."""
    if max_member <= 0 or max_total <= 0:
        raise ValueError("Size limits must be positive")
    records = []
    total = 0
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        for member in members:
            if member.is_dir():
                continue
            if member.file_size > max_member:
                raise ValueError(f"Member exceeds limit: {member.filename!r}")
            total += member.file_size
            if total > max_total:
                raise ValueError("Archive exceeds total uncompressed size limit")
            if member.flag_bits & 0x1:
                raise ValueError("Password-protected ZIP members are not supported")

            digest = hashlib.sha256()
            header = b""
            seen = 0
            with archive.open(member) as src:
                while True:
                    chunk = src.read(CHUNK)
                    if not chunk:
                        break
                    if not header:
                        header = chunk[:16]
                    seen += len(chunk)
                    if seen > max_member or seen > member.file_size:
                        raise ValueError("Member exceeds its declared size")
                    digest.update(chunk)
            records.append({
                "name": member.filename,
                "size": member.file_size,
                "modified_zip_local": "%04d-%02d-%02dT%02d:%02d:%02d" % member.date_time,
                "sha256": digest.hexdigest(),
                "file_signature": signature(header),
            })
    return {
        "archive_name": path.name,
        "archive_sha256": sha256_file(path),
        "file_count": len(records),
        "total_uncompressed": total,
        "members": records,
        "warning": "ZIP dates have unspecified timezone. File signatures are only indicative.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archives", type=Path, nargs="+")
    parser.add_argument("--max-member-mib", type=int, default=64)
    parser.add_argument("--max-total-mib", type=int, default=256)
    args = parser.parse_args(argv)
    try:
        output = [
            inventory(p, args.max_member_mib * 1024 * 1024,
                      args.max_total_mib * 1024 * 1024)
            for p in args.archives
        ]
    except (OSError, zipfile.BadZipFile, RuntimeError, ValueError) as exc:
        print(f"Cannot inspect archive: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"archives": output}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
