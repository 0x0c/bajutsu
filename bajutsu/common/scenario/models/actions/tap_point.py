"""The `tapPoint` action: tap a normalized screen coordinate rather than a selector."""

from __future__ import annotations

from typing import Self

from pydantic import model_validator

from bajutsu.common.scenario.models._base import _Model


class TapPoint(_Model):
    """`tapPoint` action — tap a screen location by normalized coordinates (0..1), not a selector.

    The bottom rung of the stability ladder (DESIGN §5), for a control the accessibility tree does
    not expose as an addressable element — most notably a tab-bar tab on an app with no accessibility
    ids, which iOS's accessibility tree collapses into one opaque group. `record`'s agent locates it in the screenshot
    and emits its center here; `run` replays it against the current screen size. `x`/`y` are fractions
    of the app window (top-left origin), so the tap survives a resolution change a raw-pixel tap would
    not — but it is still coordinate-based and unverifiable by selector, so prefer a real selector
    whenever the element is addressable.
    """

    x: float
    y: float

    @model_validator(mode="after")
    def _in_unit_square(self) -> Self:
        if not (0.0 <= self.x <= 1.0 and 0.0 <= self.y <= 1.0):
            raise ValueError("tapPoint x/y are normalized fractions and must be within 0..1 (§6.2)")
        return self
