"""The verdict of running one scenario K times and diffing the outcomes."""

from __future__ import annotations

from dataclasses import dataclass, field

# --- repeat-and-diff: prove determinism dynamically (BE-0049) ---
#
# Run a scenario K times under identical preconditions and report anything that varies as a
# *finding to fix*. The audit never changes a verdict and never feeds the run/CI gate.


@dataclass(frozen=True)
class RepeatReport:
    """The verdict of running one scenario K times and diffing the outcomes."""

    scenario: str
    runs: int  # K — how many times it was executed
    deterministic: bool  # every run agreed (or K < 2, nothing to compare)
    divergences: list[str] = field(default_factory=list)  # what varied, for a human to fix
