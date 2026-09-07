"""The cross-run triage seam: diagnose why one scenario intermittently flips at a fixed fingerprint."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from .cross_run_triage_context import CrossRunTriageContext
    from .triage import Triage


class CrossRunTriageAgent(Protocol):
    """The cross-run interface: diagnose why one scenario intermittently flips at a fixed fingerprint.

    The single-run `TriageAgent` reasons about one failure; this reasons about the delta between
    passing and failing runs of the same definition. AI-only — there is no deterministic
    implementation, since spotting the discriminating difference is exactly the judgement an LLM adds.
    """

    def triage_flaky(self, context: CrossRunTriageContext) -> Triage: ...
