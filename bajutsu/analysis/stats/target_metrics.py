"""One target's headline numbers for the cross-target comparison (BE-0226, BE-0404)."""

from __future__ import annotations

from dataclasses import dataclass

from .day_point import DayPoint


@dataclass(frozen=True)
class TargetMetrics:
    """One target's headline numbers for the cross-target comparison (BE-0226, repointed by BE-0404).

    A per-target roll-up of the same `Stats` `aggregate_runs` already computes, reduced to the
    scalars a comparison ranks on plus a trend series for a sparkline. `flaky_rate` is a plain
    count over the BE-0102/BE-0049 per-scenario classification (flaky-classified ÷ total),
    adding no new flakiness heuristic. Both counts are over distinct scenarios, not over the per-OS
    series (BE-0358), so a wider device matrix neither inflates nor deflates the rate.
    """

    name: str
    runs: int
    pass_rate: float  # Stats.pass_rate over the window
    flaky_rate: float  # flaky-classified scenarios / total scenarios (0.0 when none)
    duration_p50_s: float  # median per-run wall-clock over the window
    duration_p95_s: float  # 95th-percentile per-run wall-clock
    trend: list[DayPoint]  # daily pass-rate, oldest first — the comparison sparkline
