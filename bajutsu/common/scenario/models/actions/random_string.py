"""The `random.string` generator: characters drawn from a charset."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from bajutsu.common.scenario.models._base import _Model


class RandomString(_Model):
    """`random: { string: … }` — `length` characters drawn from `charset`."""

    length: int = Field(gt=0)
    charset: Literal["alnum", "alpha", "numeric", "hex"] = "alnum"
