"""The `drag` action: a real pointer drag of an element in a direction (BE-0227)."""

from __future__ import annotations

from typing import Literal, Self

from pydantic import model_validator

from bajutsu.common.scenario.models._base import _Model
from bajutsu.common.scenario.models.selector import Selector


class Drag(_Model):
    """`drag` action — a real pointer drag of an element (`on`) in a `direction` (BE-0227).

    Where `swipe`'s directional form *scrolls* (revealing off-screen content), `drag` grabs the
    element and moves it — a resize divider, a slider thumb, a reorder handle, a map inside a canvas:
    any control you drag rather than scroll. `amount` sets how far to travel as a fraction of the
    screen (0 < amount ≤ 1); omitted, a small default distance is used. It matters on the web
    backend, where a directional `swipe` is a wheel scroll (which does not move a grabbed element)
    but a `drag` is a genuine pointer drag (`move → down → move → up`). On iOS / Android a real OS
    drag both scrolls and moves handles, so `swipe`'s directional form and `drag` coincide there.
    """

    on: Selector
    direction: Literal["up", "down", "left", "right"]
    amount: float | None = None

    @model_validator(mode="after")
    def _amount_range(self) -> Self:
        if self.amount is not None and not (0.0 < self.amount <= 1.0):
            raise ValueError(
                "drag amount is a fraction of the screen and must be within 0..1 (§6.2)"
            )
        return self
