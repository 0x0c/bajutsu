"""The real clock, the only one a run uses outside a test."""

from __future__ import annotations

import time


class RealClock:
    def now(self) -> float:
        return time.monotonic()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)
