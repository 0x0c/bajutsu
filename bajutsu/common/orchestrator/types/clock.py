"""The time seam a wait is expressed through, so a test can make one deterministic."""

from __future__ import annotations

from typing import Protocol


class Clock(Protocol):
    """Time and sleep (swappable in tests to make waits deterministic)."""

    def now(self) -> float: ...
    def sleep(self, seconds: float) -> None: ...
