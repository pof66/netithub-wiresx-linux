# Copyright 2026 IU0NDT
# SPDX-License-Identifier: Apache-2.0
"""Opt-in, Linux-only HRI-200 serial test transport.

Observed single-shot frame exchanges only. Never poll in the background, open
audio/HID, operate RF/PTT, access the Internet or guess proprietary messages.

IMPORTANT: Opening an ACM serial port can change USB CDC DTR/RTS implicitly.
Callers must require explicit operator approval and isolated RF hardware.
"""
from __future__ import annotations

from dataclasses import dataclass
import fcntl
import os
from pathlib import Path
import select
import sys
import termios
import time
from typing import Callable

# Import the redacting frame parser, not the private capture decoder.
from hri200_protocol import FrameStream, FrameEvent

SERIAL_BAUD = 38400
REPLY_TIMEOUT = 2.0
# Only the requests and reply prefixes confirmed on isolated Linux hardware.
# These bytes MUST NOT be exposed via a generic arbitrary-command interface.
SAFE_OBSERVED_SEQUENCE = (
    ("M10", b"\x01M10\x04", "M10"),
    ("R6423", b"\x01R6423\x04", "R0_REDACTED"),
    ("P010000", b"\x01P010000\x04", "B0_OBSERVED_RESPONSE"),
)
_ALLOWED_BYTES = frozenset(request for _, request, _ in SAFE_OBSERVED_SEQUENCE)


@dataclass(frozen=True)
class TransactionResult:
    request: str
    reply: str
    tx_bytes: int
    rx_bytes: int
    latency_ms: float

    def redacted(self) -> dict:
        return {
            "request": self.request,
            "reply": self.reply,
            "tx_bytes": self.tx_bytes,
            "rx_bytes": self.rx_bytes,
            "latency_ms": round(self.latency_ms, 3),
            "identity": "not_disclosed",
        }


def choose_serial_endpoint(discovered: list[dict], selected: str | None = None) -> str:
    """Fail closed on zero or multiple HRI-200 serial endpoints."""
    paths = sorted({item["device"] for item in discovered
                    if item.get("vid", "").lower() == "26aa"
                    and item.get("pid", "").lower() == "0002"
                    and isinstance(item.get("device"), str)})
    if not paths:
        raise ValueError("No verified YAESU 26aa:0002 serial interface found")
    if selected is not None:
        if selected not in paths:
            raise ValueError("The selected port was not found under YAESU 26aa:0002")
        return selected
    if len(paths) != 1:
        raise ValueError("Multiple serial endpoints: select exactly one with --port")
    return paths[0]


class LinuxCDC:
    """One exclusive Linux serial session; no line-toggle ioctls are issued."""

    def __init__(self, port: str):
        self.port = port
        self._fd: int | None = None
        self._old_config: list | None = None

    def __enter__(self) -> "LinuxCDC":
        if not sys.platform.startswith("linux"):
            raise RuntimeError("Live HRI-200 serial testing is Linux-only")
        # Do not follow a spoofed /dev/tty* symlink into an arbitrary file.
        # The CLI only passes nodes verified in sysfs.
        fd = os.open(self.port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK |
                     getattr(os, "O_CLOEXEC", 0))
        self._fd = fd
        try:
            if not hasattr(termios, "TIOCEXCL"):
                raise OSError("TIOCEXCL unavailable; refusing unprotected serial access")
            fcntl.ioctl(fd, termios.TIOCEXCL)
            self._old_config = termios.tcgetattr(fd)
            cfg = termios.tcgetattr(fd)
            cfg[0] = cfg[1] = cfg[3] = 0
            cfg[2] &= ~(termios.CSIZE | termios.PARENB | termios.CSTOPB)
            if hasattr(termios, "CRTSCTS"):
                cfg[2] &= ~termios.CRTSCTS
            cfg[2] |= termios.CS8 | termios.CREAD | termios.CLOCAL
            cfg[4] = cfg[5] = termios.B38400
            cfg[6][termios.VMIN] = 0
            cfg[6][termios.VTIME] = 0
            termios.tcsetattr(fd, termios.TCSANOW, cfg)
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, exc_type, exc, tb) -> None:
        fd, old = self._fd, self._old_config
        self._fd = None
        self._old_config = None
        if fd is not None:
            try:
                if old is not None:
                    termios.tcsetattr(fd, termios.TCSANOW, old)
            finally:
                os.close(fd)

    def transact(self, request: bytes, expected_label: str,
                 timeout: float = REPLY_TIMEOUT) -> tuple[FrameEvent, float]:
        """Send one previously observed frame once; redact all received content."""
        if request not in _ALLOWED_BYTES:
            raise ValueError("Unverified serial command blocked")
        if not (0.1 <= timeout <= 5.0):
            raise ValueError("Timeout outside the approved bound")
        if self._fd is None:
            raise RuntimeError("Serial session is not open")

        fd = self._fd
        decoder = FrameStream("RX", max_body=512)
        start = time.monotonic()
        deadline = start + timeout
        written = 0
        while written < len(request):
            remain = deadline - time.monotonic()
            if remain <= 0:
                raise TimeoutError("Timeout while transmitting a verified short frame")
            _, ready, _ = select.select([], [fd], [], remain)
            if not ready:
                raise TimeoutError("Serial port not writable")
            n = os.write(fd, request[written:])
            if n <= 0:
                raise OSError("Serial write returned zero bytes")
            written += n

        # There is no retry, follow-on command or automatic repeated polling.
        while time.monotonic() < deadline:
            remain = deadline - time.monotonic()
            ready, _, _ = select.select([fd], [], [], max(remain, 0.0))
            if not ready:
                continue
            payload = os.read(fd, 512)
            if not payload:
                raise OSError("Serial port closed during response")
            events = decoder.feed(payload)
            if events:
                if len(events) != 1 or events[0].label != expected_label:
                    # Never expose unexpected payload, even in error text.
                    raise RuntimeError("Unexpected or multiple HRI-200 reply frames")
                return events[0], (time.monotonic() - start) * 1000.0
        raise TimeoutError("No matching response within bounded timeout")


def run_verified_sequence(
    transaction: Callable[[bytes, str, float], tuple[FrameEvent, float]],
    timeout: float = REPLY_TIMEOUT,
) -> list[TransactionResult]:
    """Strictly three verified requests in order, aborting at first mismatch."""
    results: list[TransactionResult] = []
    for label, request, expected in SAFE_OBSERVED_SEQUENCE:
        frame, elapsed_ms = transaction(request, expected, timeout)
        if frame.direction != "RX" or frame.label != expected:
            raise RuntimeError("Incorrect reply classification; sequence aborted")
        results.append(TransactionResult(
            request=label,
            reply=frame.label,
            tx_bytes=len(request),
            rx_bytes=frame.body_length + 2,
            latency_ms=elapsed_ms,
        ))
    return results
