"""The `gone` assertion: an element has left the screen."""

from __future__ import annotations

from bajutsu.common.scenario.models._base import _Model
from bajutsu.common.scenario.models.selector import Selector


class Gone(_Model):
    """`until: { gone: <Selector> }` — wait until a selector no longer matches any element."""

    gone: Selector
