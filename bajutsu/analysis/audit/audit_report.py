"""A scenario's determinism score and the findings behind it, the audit's per-scenario verdict."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .finding import Finding


@dataclass(frozen=True)
class AuditReport:
    """The per-scenario determinism score, parallel to doctor's id-coverage score."""

    scenario: str
    selectors: int  # selectors graded
    stable: int  # resolve by a unique id (id / idMatches)
    moderate: int  # resolve by label / traits / value (auxiliary, no id)
    fragile: int  # rely on index (the flaky last resort)
    stability: float  # stable / selectors (1.0 when no selectors)
    grade: str  # "Stable" | "Moderate" | "Fragile"
    findings: list[Finding]
