# Copyright 2026 IU0NDT
# SPDX-License-Identifier: Apache-2.0
"""HRI-200 observed CDC framing engine: pure, offline and side-effect free.

Input is a byte stream supplied by a caller. This module never opens serial
ports, toggles DTR/RTS, writes to USB, connects to the Internet or transmits RF.

In one private Windows 2.010 capture the serial application protocol used
0x01 + ASCII bytes + 0x04. Names are *observed patterns*, not decoded radio
semantics. All emitted events are redacted by design.
"""
from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from typing import Optional

START = 0x01
END = 0x04
DEFAULT_MAX_FRAME_BODY = 4096
DEFAULT_MAX_PENDING_POLLS = 4096

# These byte strings were verified in the operator's private USBPcap capture.
# They are labels for passive observation, NOT commands to send to hardware.
OBSERVED_FRAMES = {
    b"M10": "M10",
    b"R6423": "R6423",
    b"P010000": "P010000",
    b"B0 0    0000000": "B0_OBSERVED_RESPONSE",
    b"D1V0000": "D1V0000",
}


@dataclass(frozen=True)
class FrameEvent:
    """Privacy-safe classification; the raw frame is intentionally discarded."""

    direction: str
    label: str
    body_length: int
    timestamp: Optional[float] = None


def classify(body: bytes) -> str:
    """Never return a body or identity-bearing string."""
    # Identity-bearing R0 must be redacted even if corrupt or not hex.
    if body.startswith(b"R0"):
        return "R0_REDACTED"
    return OBSERVED_FRAMES.get(body, "UNKNOWN_REDACTED")


class FrameStream:
    """Incremental, bounded STX/ETX parser for exactly one byte-stream direction.

    Handles split transfers, multiple frames in one transfer, stray bytes,
    unexpectedly repeated STX and malicious oversized frames. After an
    oversized frame it ignores bytes until the next STX.
    """

    def __init__(self, direction: str, max_body: int = DEFAULT_MAX_FRAME_BODY):
        if direction not in ("RX", "TX"):
            raise ValueError("direction must be RX or TX")
        if max_body < 1:
            raise ValueError("max_body must be positive")
        self.direction = direction
        self.max_body = max_body
        self._buffer = bytearray()
        self._in_frame = False
        self._discarding = False
        self.stats: Counter[str] = Counter()

    @property
    def incomplete(self) -> bool:
        return self._in_frame

    def feed(self, chunk: bytes, timestamp: Optional[float] = None) -> list[FrameEvent]:
        events: list[FrameEvent] = []
        for byte in chunk:
            if byte == START:
                if self._in_frame:
                    self.stats["resync"] += 1
                self._buffer.clear()
                self._in_frame = True
                self._discarding = False
                continue
            if not self._in_frame:
                self.stats["ignored_outside_frame"] += 1
                continue
            if byte == END:
                if not self._discarding:
                    events.append(
                        FrameEvent(self.direction, classify(self._buffer),
                                   len(self._buffer), timestamp)
                    )
                    self.stats["frames"] += 1
                self._buffer.clear()
                self._in_frame = False
                self._discarding = False
                continue
            if self._discarding:
                continue
            if len(self._buffer) >= self.max_body:
                self.stats["oversized"] += 1
                self._buffer.clear()
                self._discarding = True
                continue
            self._buffer.append(byte)
        return events


class PassiveSession:
    """Aggregate observed frames and rough FIFO P->B latency on an offline stream.

    This is NOT a working HRI-200 protocol implementation. It never initiates
    requests and never publishes raw payloads, device IDs or R0 data.
    """

    def __init__(self, max_body: int = DEFAULT_MAX_FRAME_BODY,
                 max_pending_polls: int = DEFAULT_MAX_PENDING_POLLS):
        if max_pending_polls < 1:
            raise ValueError("max_pending_polls must be positive")
        self.rx = FrameStream("RX", max_body)
        self.tx = FrameStream("TX", max_body)
        self.counts: Counter[str] = Counter()
        self._pending: deque[float] = deque()
        self._max_pending = max_pending_polls
        self._latency_count = 0
        self._latency_total_ms = 0.0
        self._latency_min_ms: Optional[float] = None
        self._latency_max_ms: Optional[float] = None

    def observe(self, direction: str, data: bytes,
                timestamp: Optional[float] = None) -> list[FrameEvent]:
        if direction not in ("RX", "TX"):
            raise ValueError("direction must be RX or TX")
        parser = self.rx if direction == "RX" else self.tx
        frames = parser.feed(data, timestamp=timestamp)
        for event in frames:
            self.counts[event.direction + ":" + event.label] += 1
            if event.direction == "TX" and event.label == "P010000":
                if timestamp is not None:
                    if len(self._pending) >= self._max_pending:
                        self._pending.popleft()
                        self.counts["dropped_pending_poll"] += 1
                    self._pending.append(timestamp)
            elif (event.direction == "RX"
                  and event.label == "B0_OBSERVED_RESPONSE" and self._pending
                  and timestamp is not None):
                latency_ms = (timestamp - self._pending[0]) * 1000.0
                # Negative offsets are discarded: not a plausible paired reply.
                if latency_ms < 0:
                    self.counts["negative_pair_timestamp"] += 1
                    continue
                self._pending.popleft()
                self._latency_count += 1
                self._latency_total_ms += latency_ms
                self._latency_min_ms = (
                    latency_ms if self._latency_min_ms is None
                    else min(self._latency_min_ms, latency_ms)
                )
                self._latency_max_ms = (
                    latency_ms if self._latency_max_ms is None
                    else max(self._latency_max_ms, latency_ms)
                )
        return frames

    def report(self) -> dict:
        return {
            "schema": "netithub-hri200-passive-session-v1",
            "mode": "offline_observation_only",
            "observed_frames": dict(sorted(self.counts.items())),
            "rx_frames": self.rx.stats["frames"],
            "tx_frames": self.tx.stats["frames"],
            "rx_resync": self.rx.stats["resync"],
            "tx_resync": self.tx.stats["resync"],
            "rx_oversized": self.rx.stats["oversized"],
            "tx_oversized": self.tx.stats["oversized"],
            "incomplete_streams": {
                "RX": self.rx.incomplete,
                "TX": self.tx.incomplete,
            },
            "poll_response_fifo": {
                "pairs": self._latency_count,
                "unpaired_requests": len(self._pending),
                "minimum_ms": (
                    round(self._latency_min_ms, 3)
                    if self._latency_min_ms is not None else None
                ),
                "mean_ms": (
                    round(self._latency_total_ms / self._latency_count, 3)
                    if self._latency_count else None
                ),
                "maximum_ms": (
                    round(self._latency_max_ms, 3)
                    if self._latency_max_ms is not None else None
                ),
            },
            "limitations": (
                "No HRI-200 serial I/O, YAESU network authentication, "
                "RF activity, or decoded PTT/audio semantics"
            ),
        }
