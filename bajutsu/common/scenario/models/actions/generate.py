"""The `generate` action: compute a random or datetime value into a variable (BE-0377)."""

from __future__ import annotations

from typing import Self

from pydantic import model_validator

from bajutsu.common.scenario.models._base import _exactly_one, _Model

from .datetime_value import DatetimeValue
from .random_value import RandomValue
from .var_target import VarTarget


class Generate(_Model):
    """`generate` — compute a random or current-datetime value into `${vars.*}` (BE-0377).

    Exactly one generator kind produces the value, and `into.var` names the slot a later `type` /
    `assert` reads it from — the same placement `totp` uses. Local and deterministic: a generator
    draw or a clock read, never a model and never the network. Only the *value* varies between
    runs; a step the validator accepted always executes and always succeeds.
    """

    random: RandomValue | None = None
    datetime: DatetimeValue | None = None
    into: VarTarget

    @model_validator(mode="after")
    def _one_kind(self) -> Self:
        _exactly_one(self, ("random", "datetime"), "§6.2")
        return self
