"""The authoring-agent seam: propose the next action from one observation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from .observation import Observation
    from .proposal import Proposal


class Agent(Protocol):
    """The authoring agent: proposes the next action from an observation."""

    def next_action(self, observation: Observation) -> Proposal: ...

    def plan(self, goal: str) -> list[str]:
        """Decompose `goal` into an ordered list of concrete, human-readable steps.

        Called once before the record loop starts so the procedure can be explained to
        the watcher and fed back to the agent each turn (via `Observation.plan`). Optional:
        the loop treats a missing `plan` (or one that returns []) as "no up-front plan".
        """
        ...
