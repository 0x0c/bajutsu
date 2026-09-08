"""A proposer's output for one screen."""

from __future__ import annotations

from dataclasses import dataclass, field

from bajutsu.crawl import core as crawl


@dataclass
class Proposal:
    """The proposer's output for one screen.

    The operations to try, plus `thought` — the model's short reasoning, surfaced live so a watcher
    sees what the AI is doing.
    """

    actions: list[crawl.Action] = field(default_factory=list)
    thought: str = ""
    tokens: int = 0  # tokens the model spent on this proposal (0 when unknown / no AI call)
