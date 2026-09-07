"""The `if` step: deterministic conditional execution."""

from __future__ import annotations

from pydantic import Field

from bajutsu.common.scenario.models._base import _Model
from bajutsu.common.scenario.models.assertions import Assertion

from .step import Step


class If(_Model):
    """Conditional execution.

    Evaluate an assertion as the condition, then run ``then`` steps if it passes or ``else`` steps
    otherwise.
    """

    condition: Assertion
    then: list[Step] = Field(default_factory=list)
    else_: list[Step] | None = Field(default=None, alias="else")
