"""One day's usage — the ledger trend line at day granularity."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DayPoint:
    """One day's usage — the trend line at day granularity."""

    day: str  # YYYY-MM-DD, or "" for a line whose ts carries no date
    calls: int
    tokens: int
    cost: float
