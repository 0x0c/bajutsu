"""The `random` generator's shape: exactly one generator kind (BE-0377)."""

from __future__ import annotations

from typing import Self

from pydantic import Field, model_validator

from bajutsu.common.scenario.models._base import _exactly_one, _Model

from .random_float import RandomFloat
from .random_int import RandomInt
from .random_string import RandomString
from .random_uuid import RandomUuid


class RandomValue(_Model):
    """`generate: { random: … }` — exactly one generator kind (BE-0377)."""

    string: RandomString | None = None
    # `int` / `float` shadow builtins, so the field is suffixed and aliased to the YAML key, the
    # same way `copy_` / `assert_` / `if_` already are.
    int_: RandomInt | None = Field(default=None, alias="int")
    float_: RandomFloat | None = Field(default=None, alias="float")
    uuid: RandomUuid | None = None

    @model_validator(mode="after")
    def _one_kind(self) -> Self:
        _exactly_one(self, ("string", "int_", "float_", "uuid"), "§6.2")
        return self
