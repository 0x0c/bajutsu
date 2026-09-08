"""Aggregate run-stats dashboard (BE-0102) — the deterministic trend across many runs.

A read-only aggregation over the artifacts the runner already writes (`manifest.json` per run): it
turns a pile of runs into a picture — pass-rate over time, run/scenario durations, the scenarios and
steps that fail most, per-scenario flakiness, and run volume. Every figure is an exact count or
aggregation; there is no model and no verdict, and it is never part of the CI gate (a team may
*track* a number from it as informational, exactly as the coverage map allows).

It is the operational complement to the two analytical reports Bajutsu already ships — the coverage
map (BE-0050) answers *"what surface do we test?"* and the determinism audit (BE-0049) answers *"is a
given scenario reproducible?"*; this answers *"how is the whole suite doing over time?"* The
scenario-level series are keyed by the BE-0049 `(scenarioHash, name)` identity, widened with the
parsed device OS (BE-0358) — a verdict that flips at a constant fingerprint on one OS is true
flakiness, while an edited scenario, or the same scenario on another OS version, starts a fresh
series — and the flakiness classification is reused from the audit rather than re-derived.
"""

from ._functions import _RUN_DAY as _RUN_DAY
from ._functions import _TEMPLATE_DIR as _TEMPLATE_DIR
from ._functions import _as_float as _as_float
from ._functions import _as_list as _as_list
from ._functions import _as_str as _as_str
from ._functions import _by_backend as _by_backend
from ._functions import _by_day as _by_day
from ._functions import _day_of as _day_of
from ._functions import _env as _env
from ._functions import _failing_assertions as _failing_assertions
from ._functions import _failing_scenarios as _failing_scenarios
from ._functions import _failing_steps as _failing_steps
from ._functions import _flaky as _flaky
from ._functions import _opt_float as _opt_float
from ._functions import _percentile as _percentile
from ._functions import _run_point as _run_point
from ._functions import _scenario_durations as _scenario_durations
from ._functions import _slowest as _slowest
from ._functions import _str_or as _str_or
from ._functions import _top_reason as _top_reason
from ._functions import aggregate_runs, render, render_html, target_metrics
from ._hotspot_tally import _HotspotTally as _HotspotTally
from .day_point import DayPoint
from .hotspot import Hotspot
from .run_point import RunPoint
from .scenario_stat import ScenarioStat
from .stats import Stats
from .target_metrics import TargetMetrics

__all__ = [
    "DayPoint",
    "Hotspot",
    "RunPoint",
    "ScenarioStat",
    "Stats",
    "TargetMetrics",
    "aggregate_runs",
    "render",
    "render_html",
    "target_metrics",
]
