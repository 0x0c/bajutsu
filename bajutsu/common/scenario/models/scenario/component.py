"""A reusable, parameterized sequence of steps."""

from __future__ import annotations

from pydantic import Field

from bajutsu.common.scenario.models._base import _Model
from bajutsu.common.scenario.models.steps import Step


class Component(_Model):
    """A reusable, parameterized sequence of steps.

    `params` are the names a caller must supply via `use: { with: {...} }`; the steps reference them
    as `${params.<name>}`.
    """

    params: list[str] = Field(default_factory=list)
    steps: list[Step]
