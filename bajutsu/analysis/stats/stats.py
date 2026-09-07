"""The whole-suite trend: run totals, the time series, per-scenario aggregates, and hotspots."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .day_point import DayPoint
    from .hotspot import Hotspot
    from .run_point import RunPoint
    from .scenario_stat import ScenarioStat


@dataclass(frozen=True)
class Stats:
    """The whole-suite trend: run totals, the time series, per-scenario aggregates, and hotspots."""

    runs: int
    passed_runs: int
    failed_runs: int
    pass_rate: float
    total_duration_s: float  # summed run wall-clock across the whole set
    by_run: list[RunPoint]  # chronological (oldest first) — pass-rate over time and volume
    by_day: list[DayPoint]  # chronological (oldest first)
    by_backend: dict[str, int]  # run count per actuator — the volume denominator
    # Per (fingerprint, scenario, OS) — so one scenario can hold several rows, one per OS version
    # it ran on (BE-0358). Flaky first, then most-observed.
    scenarios: list[ScenarioStat]
    failing_scenarios: list[Hotspot]  # scenarios that fail most, by frequency
    failing_steps: list[Hotspot]  # step actions that fail most, by frequency
    failing_assertions: list[Hotspot]  # assertion kinds that fail most, by frequency
    scenarios_skipped: int  # runs with no scenarioHash — can't join a fingerprinted series
