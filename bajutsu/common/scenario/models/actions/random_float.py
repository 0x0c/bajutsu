"""The `random.float` generator: a number in a range, at a stated precision."""

from __future__ import annotations

from typing import Self

from pydantic import Field, model_validator

from bajutsu.common.scenario.models._base import _Model


class RandomFloat(_Model):
    """`random: { float: … }` — a number in `[min, max]`, rounded to `precision` decimal places."""

    min: float
    max: float
    precision: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        if self.min > self.max:
            raise ValueError(f"random.float: min must not exceed max ({self.min} > {self.max})")
        return self
