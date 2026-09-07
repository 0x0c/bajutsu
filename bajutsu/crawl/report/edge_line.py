"""One transition drawn as an SVG path, with its alert marker's anchor."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EdgeLine:
    """One transition drawn as an SVG path, with the alert marker's anchor."""

    d: str  # SVG path data (a bezier from the source card's right edge to the target's left)
    alert: bool  # the transition tapped through an OS prompt the guard dismissed
    mark_x: int
    mark_y: int
