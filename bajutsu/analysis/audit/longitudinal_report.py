"""Flakiness mined from accumulated run history, scenario by scenario."""

from __future__ import annotations

from dataclasses import dataclass

from .scenario_history import ScenarioHistory


@dataclass(frozen=True)
class LongitudinalReport:
    """Flakiness mined from accumulated run history — each scenario's verdict over its own past."""

    histories: list[
        ScenarioHistory
    ]  # one per (fingerprint, scenario, OS), flaky first then by run count
    skipped: int  # runs with no `scenarioHash` provenance — can't be grouped by identity
