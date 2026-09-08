"""The step a failed run stopped on, reduced to what triage reasons about."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FailedStep:
    """The step that failed — its index, action, and failure reason."""

    index: int
    action: str
    reason: str
