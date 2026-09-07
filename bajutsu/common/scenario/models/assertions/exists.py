"""The `exists` assertion: an element is present, or deliberately absent."""

from __future__ import annotations

from typing import Any

from pydantic import model_validator

from bajutsu.common.scenario.models._base import _Model
from bajutsu.common.scenario.models.selector import Selector


class Exists(_Model):
    """`exists: { <selector>, negate? }` (selector inline, optional negate)."""

    sel: Selector
    negate: bool = False

    @model_validator(mode="before")
    @classmethod
    def _inline(cls, data: Any) -> Any:
        if isinstance(data, dict) and "sel" not in data:
            d = dict(data)
            negate = d.pop("negate", False)
            return {"sel": d, "negate": negate}
        return data
