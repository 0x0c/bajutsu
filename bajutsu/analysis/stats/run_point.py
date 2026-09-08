"""One run as a point on the trend line — pass-rate-over-time and volume both read this."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RunPoint:
    """One run as a point on the trend line — pass-rate-over-time and volume both read this."""

    run_id: str
    day: str  # YYYY-MM-DD parsed from run_id, "" when the id carries no timestamp
    ok: bool  # the run's top-level verdict
    passed: int  # scenarios that passed in this run
    total: int  # scenarios in this run
    duration_s: float  # the run's wall-clock, summed from its scenarios' durations
    backend: str  # the actuator that drove the run ("xcuitest" / "fake" / …)
