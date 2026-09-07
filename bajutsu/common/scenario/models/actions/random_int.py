"""The `random.int` generator: an integer in an inclusive range."""

from __future__ import annotations

from typing import Self

from pydantic import model_validator

from bajutsu.common.scenario.models._base import _Model


class RandomInt(_Model):
    """`random: { int: … }` — an integer in the inclusive range `[min, max]`."""

    min: int
    max: int

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        if self.min > self.max:
            raise ValueError(f"random.int: min must not exceed max ({self.min} > {self.max})")
        return self
