"""A rectangle a visual comparison ignores — a clock, a status bar."""

from __future__ import annotations

from bajutsu.common.scenario.models._base import _Model


class ExcludeRegion(_Model):
    """A rectangular region to ignore during visual comparison (e.g. status bar, clock).

    Coordinates are in screenshot pixels — a fixed box, stable only while the layout is.
    Use `SelectorRegion` to mask by element instead, which survives reflow and resolution changes.
    """

    x: float
    y: float
    w: float
    h: float
