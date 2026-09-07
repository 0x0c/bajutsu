"""One failing scenario as it appears in a run-completion notification."""

from __future__ import annotations

from typing import TypedDict

# ---------------------------------------------------------------------------
# Summary model (format-neutral)
# ---------------------------------------------------------------------------


class FailureSummary(TypedDict):
    scenario: str
    failure: str
    duration_s: float
