"""The `extract` modifier: capture an element's property into a runtime variable."""

from __future__ import annotations

from typing import Literal

from bajutsu.common.scenario.models._base import _Model
from bajutsu.common.scenario.models.selector import Selector


class Extract(_Model):
    """Capture a UI element's property into a runtime variable (``vars.*``)."""

    sel: Selector
    prop: Literal["value", "label", "identifier"] = "value"
