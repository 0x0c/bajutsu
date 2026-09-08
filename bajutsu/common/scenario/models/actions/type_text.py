"""The `type` action: enter text, optionally into a selector and optionally submitting."""

from __future__ import annotations

from bajutsu.common.scenario.models._base import _Model
from bajutsu.common.scenario.models.selector import Selector


class TypeText(_Model):
    """`type` action — enter text, optionally into a selector and optionally submitting after."""

    text: str
    into: Selector | None = None
    submit: bool = False
