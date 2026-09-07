"""An evidence kind that was asked for and no backend could supply (BE-0020)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SkippedCapture:
    """An evidence kind that was requested but no backend could supply (BE-0020).

    Recorded per scenario so a gap is disclosed in the manifest/report rather than left silently
    empty — graceful degradation, never a run failure.
    """

    kind: str  # the evidence kind, e.g. "network"
    reason: str  # why it was skipped, e.g. "no same-platform backend provides network"
