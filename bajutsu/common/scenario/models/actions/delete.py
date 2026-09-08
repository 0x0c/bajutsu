"""The `delete` action: remove characters from the end of a field (BE-0265)."""

from __future__ import annotations

from pydantic import Field

from bajutsu.common.scenario.models._base import _Model
from bajutsu.common.scenario.models.selector import Selector


class Delete(_Model):
    """`delete` action — remove `count` characters from the end of the field (backspace; BE-0265)."""

    into: Selector
    count: int = Field(gt=0)
