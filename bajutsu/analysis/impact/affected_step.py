from __future__ import annotations

from dataclasses import dataclass

from .reference import Reference
from .step_ref import StepRef


@dataclass(frozen=True, order=True)
class AffectedStep:
    """A step the change is likely to affect, with the references that implicate it (the *why*)."""

    step: StepRef
    reasons: list[Reference]
