"""The `for` wait: the condition a step blocks on, never a fixed sleep."""

from __future__ import annotations

from typing import Literal, Self

from pydantic import Field, model_validator

from bajutsu.common.scenario.models._base import _Model
from bajutsu.common.scenario.models.selector import Selector

from .gone import Gone
from .wait_request import WaitRequest


class Wait(_Model):
    """`wait` step — block until a selector appears (`for`) or a condition holds (`until`).

    Bounded by `timeout`; always a condition wait, never a fixed sleep.
    """

    for_: Selector | None = Field(default=None, alias="for")
    # settled = wait until the screen stops changing (best-effort; for transition settle)
    until: Literal["screenChanged", "settled"] | Gone | WaitRequest | None = None
    timeout: float

    @model_validator(mode="after")
    def _one(self) -> Self:
        if (self.for_ is None) == (self.until is None):
            raise ValueError("wait requires exactly one of 'for' or 'until' (§6.3)")
        return self
