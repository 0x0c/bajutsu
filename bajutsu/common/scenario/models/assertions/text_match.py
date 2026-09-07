"""How an assertion compares text: equals, contains, or a regular expression."""

from __future__ import annotations

from typing import Self

from pydantic import model_validator

from bajutsu.common.scenario.models._base import _Model
from bajutsu.common.scenario.models.selector import Selector


class TextMatch(_Model):
    """`value` / `label`: exactly one of equals / contains / matches."""

    sel: Selector
    equals: str | None = None
    contains: str | None = None
    matches: str | None = None

    @model_validator(mode="after")
    def _one_op(self) -> Self:
        if sum(o is not None for o in (self.equals, self.contains, self.matches)) != 1:
            raise ValueError("value/label requires exactly one of equals/contains/matches (§6.4)")
        return self
