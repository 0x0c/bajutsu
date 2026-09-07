"""The enrichment seam: propose assertions for a scenario whose steps are already replayed."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from bajutsu.common.scenario import Scenario

if TYPE_CHECKING:
    from .enrichment_proposal import EnrichmentProposal
    from .step_context import StepContext


class EnrichmentAgent(Protocol):
    """Proposes assertions for a scenario whose steps have already been replayed."""

    def propose_assertions(
        self,
        scenario: Scenario,
        step_contexts: list[StepContext],
    ) -> EnrichmentProposal: ...
