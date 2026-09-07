"""The `scroll` action: scroll until a target is on screen, or fail at a bound (BE-0326)."""

from __future__ import annotations

from typing import Literal, Self

from pydantic import Field, model_validator

from bajutsu.common.scenario.models._base import _Model
from bajutsu.common.scenario.models.selector import Selector


class Scroll(_Model):
    """`scroll` action — scroll a region until `to` is on-screen, or fail at a bound (BE-0326).

    Where `swipe`'s directional form is a *single* gesture, `scroll` is a bounded condition wait: it
    scrolls one non-inertial step, re-queries, and stops the moment `to` resolves with its frame's
    center inside the viewport — the point a following coordinate `tap` would aim at. It fails
    deterministically when it spends `maxScrolls` steps, or as soon as a step no longer changes the
    scrolled region's subtree (the region has bottomed out and the target is not there).

    `direction` names the direction the *content* scrolls, so `down` reveals items below the fold —
    the inverse of `swipe`, whose `direction` is the finger's. `within` scopes the gesture (and the
    end-of-content comparison) to one scrollable container; omitted, the whole screen scrolls.

    `amount` sets how far one step travels, as a fraction of the viewport (0 < amount ≤ 1) — the same
    unit `swipe` and `drag` take — for a screen whose content the default step size overshoots or
    creeps across. Omitted, the loop keeps its own default. It sets only where the loop *starts*: the
    overshoot recovery still shrinks the step toward its own fixed floor from wherever `amount` put
    it (BE-0400).
    """

    to: Selector
    direction: Literal["up", "down", "left", "right"] = "down"
    within: Selector | None = None
    amount: float | None = None
    max_scrolls: int = Field(default=15, alias="maxScrolls", gt=0)

    @model_validator(mode="after")
    def _amount_range(self) -> Self:
        if self.amount is not None and not (0.0 < self.amount <= 1.0):
            raise ValueError(
                "scroll amount is a fraction of the viewport and must be within 0..1 (§6.2)"
            )
        return self
