"""How to clear a detected system prompt: the button's center in normalized coordinates."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AlertDecision:
    """How to clear a detected prompt: the button center in normalized coords."""

    present: bool
    x: float = 0.0  # button center x as a fraction [0,1] of screen width
    y: float = 0.0  # button center y as a fraction [0,1] of screen height
    label: str = ""  # the button's text, for logging
