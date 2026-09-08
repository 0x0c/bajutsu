"""A recurring failure ranked by frequency — a scenario, a step action, or an assertion kind."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Hotspot:
    """A recurring failure ranked by frequency — a scenario, a step action, or an assertion kind."""

    key: str  # the scenario name / "scenario > action" / assertion kind that failed
    failures: int
    reason: str  # the most frequent failure reason among those failures ("" when none was recorded)
    run_ids: tuple[str, ...]  # sorted, deduped ids of the runs this failure occurred in (BE-0241)
