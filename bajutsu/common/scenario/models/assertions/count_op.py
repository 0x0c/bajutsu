"""A count comparison with no selector of its own."""

from __future__ import annotations

from typing import Self

from pydantic import Field, model_validator

from bajutsu.common.scenario.models._base import _Model


class CountOp(_Model):
    """A count comparison with no element selector — exactly one of equals / atLeast / atMost.

    The element-free counterpart to `CountMatch`, for aggregating over the network timeline (e.g. an
    `event`'s multiplicity) rather than over screen elements.
    """

    equals: int | None = None
    at_least: int | None = Field(default=None, alias="atLeast")
    at_most: int | None = Field(default=None, alias="atMost")

    @model_validator(mode="after")
    def _one_op(self) -> Self:
        if sum(o is not None for o in (self.equals, self.at_least, self.at_most)) != 1:
            raise ValueError("count requires exactly one of equals/atLeast/atMost (§6.4)")
        return self
