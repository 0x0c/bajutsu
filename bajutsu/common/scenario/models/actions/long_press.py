"""The `longPress` action: press and hold a selector for a stated duration."""

from __future__ import annotations

from bajutsu.common.scenario.models._base import _Model
from bajutsu.common.scenario.models.selector import Selector


class LongPress(_Model):
    """`longPress` action — press and hold a selector for `duration` seconds."""

    sel: Selector
    duration: float
