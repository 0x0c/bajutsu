"""The `count` assertion: how many elements a selector resolves to."""

from __future__ import annotations

from typing import Self

from pydantic import Field, model_validator

from bajutsu.common.scenario.models._base import _Model
from bajutsu.common.scenario.models.selector import Selector


class CountMatch(_Model):
    """`count`: exactly one of equals / atLeast / atMost."""

    sel: Selector
    equals: int | None = None
    at_least: int | None = Field(default=None, alias="atLeast")
    at_most: int | None = Field(default=None, alias="atMost")

    @model_validator(mode="after")
    def _one_op(self) -> Self:
        if sum(o is not None for o in (self.equals, self.at_least, self.at_most)) != 1:
            raise ValueError("count requires exactly one of equals/atLeast/atMost (§6.4)")
        return self
