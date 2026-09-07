"""The `forEach` step: iterate over the elements a selector resolves to."""

from __future__ import annotations

from pydantic import Field

from bajutsu.common.scenario.models._base import _Model
from bajutsu.common.scenario.models.selector import Selector

from .step import Step


class ForEach(_Model):
    """Iterate over elements matching a selector.

    Each element's identifier is stored as ``vars.<as>`` and the nested steps are executed.
    """

    sel: Selector
    as_: str = Field(alias="as")
    steps: list[Step] = Field(default_factory=list)
