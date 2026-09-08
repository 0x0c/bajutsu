"""The delta material cross-run triage reasons over (BE-0220)."""

from __future__ import annotations

from dataclasses import dataclass

from .run_evidence import RunEvidence


@dataclass(frozen=True)
class CrossRunTriageContext:
    """The delta material to reason about why one scenario intermittently passes and fails (BE-0220).

    Unlike `TriageContext` (one failed run), this gathers the same scenario's evidence across
    several of its passing and failing runs at a fixed content fingerprint, so an investigator can
    reason about what *varies* between a pass and a fail — the cross-run counterpart to per-failure
    triage.
    """

    scenario: str
    scenario_hash: str | None  # the runs' shared fingerprint, when known (the grouping key)
    scenario_yaml: str  # the scenario's definition (shared across the runs at one fingerprint)
    target_id: str | None  # the failing step's selector id, if any
    passing: list[RunEvidence]
    failing: list[RunEvidence]
