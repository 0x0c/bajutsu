from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class StepRef:
    """One scenario step (or scenario-level position) a reference points at.

    `index` is the step's 1-origin position in the scenario's step list; `0` marks a scenario-level
    reference that no single step owns — a `preconditions` screen or a scenario-level `expect`.
    """

    scenario: str
    index: int
    label: str  # `step.name`, else the action key (`tap`), else `setup` / `deeplink` / `expect`
