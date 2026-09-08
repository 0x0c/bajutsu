"""The assertions an enrichment agent proposes for an existing scenario."""

from __future__ import annotations

from dataclasses import dataclass, field

from bajutsu.common.scenario import Assertion, Step


@dataclass
class EnrichmentProposal:
    """The agent's proposed assertions for an existing scenario."""

    expect: list[Assertion] = field(default_factory=list)
    settle: Step | None = None
    note: str = ""
