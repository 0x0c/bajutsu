"""The `rotate` action: a two-finger rotation by an angle."""

from __future__ import annotations

from bajutsu.common.scenario.models._base import _Model
from bajutsu.common.scenario.models.selector import Selector


class Rotate(_Model):
    """Two-finger rotation. radians > 0 rotates clockwise."""

    sel: Selector
    radians: float
