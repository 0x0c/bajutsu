"""A day's run pass-rate — the trend line at day granularity."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DayPoint:
    """A day's run pass-rate — the trend line at day granularity."""

    day: str  # YYYY-MM-DD, or "" for runs whose id carries no timestamp
    runs: int
    passed_runs: int
    pass_rate: float  # passed_runs / runs
