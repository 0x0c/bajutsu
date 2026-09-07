"""What an authoring agent sees on one turn: the goal, the screen, and the history so far."""

from __future__ import annotations

from dataclasses import dataclass, field

from bajutsu.common.drivers import base
from bajutsu.common.scenario import Step


@dataclass
class Observation:
    """What the agent sees one turn: the goal, the current screen, and history so far."""

    goal: str
    screen: list[base.Element]
    history: list[Step]
    screenshot: bytes | None = None  # PNG bytes of the current screen, for vision
    plan: list[str] = field(default_factory=list)  # the goal decomposed into ordered concrete steps
    # Whether this session can ever supply a screenshot (BE-0192). False in `--no-screenshot` mode,
    # where vision is off for every turn — so the agent must not be nudged to escalate for one it
    # can never get. When True, a `screenshot is None` turn is merely on-demand-skipped, not blind.
    vision_available: bool = True
