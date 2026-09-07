from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .reference import Reference
    from .step_ref import StepRef


@dataclass(frozen=True)
class ReverseIndex:
    """Each referenced literal mapped to the steps that reference it (both sides sorted). Pure."""

    entries: dict[Reference, list[StepRef]]
