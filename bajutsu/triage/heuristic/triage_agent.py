"""The triage seam: turn one failed scenario's context into a verdict."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from .triage import Triage
    from .triage_context import TriageContext


class TriageAgent(Protocol):
    """The triage interface: turn a failed scenario's context into a `Triage` verdict.

    Implemented by the deterministic `HeuristicTriageAgent` (no AI) and by AI-backed agents alike.
    """

    def triage(self, context: TriageContext) -> Triage: ...
