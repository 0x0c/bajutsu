"""The `swipe` action: by direction on an element, or between two points."""

from __future__ import annotations

from typing import Literal, Self

from pydantic import Field, model_validator

from bajutsu.common.scenario.models._base import Point, _Model
from bajutsu.common.scenario.models.selector import Selector


class Swipe(_Model):
    """`swipe` action — by `direction` on an element (`on`), or between two points (`from`/`to`).

    `amount` (only with `on`/`direction`) sets how far to travel as a fraction of the screen
    (0 < amount ≤ 1): ~0.2 nudges, ~0.5 scrolls half a screen, ~0.9 nearly a full one. Omitted, a
    small default distance is used — so the caller can dial the scroll to the instruction.
    """

    on: Selector | None = None
    direction: Literal["up", "down", "left", "right"] | None = None
    amount: float | None = None
    from_: Point | None = Field(default=None, alias="from")
    to: Point | None = None

    @model_validator(mode="after")
    def _form(self) -> Self:
        sel_fields = self.on is not None or self.direction is not None
        pt_fields = self.from_ is not None or self.to is not None
        if sel_fields and pt_fields:
            raise ValueError("swipe cannot mix {on,direction} with {from,to} (§6.2)")
        if self.amount is not None and not (0.0 < self.amount <= 1.0):
            raise ValueError(
                "swipe amount is a fraction of the screen and must be within 0..1 (§6.2)"
            )
        if self.on is not None and self.direction is not None:
            return self
        if self.amount is not None:
            raise ValueError("swipe amount applies only to the {on,direction} form (§6.2)")
        if self.from_ is not None and self.to is not None:
            return self
        raise ValueError("swipe requires either {on,direction} or {from,to} completely (§6.2)")
