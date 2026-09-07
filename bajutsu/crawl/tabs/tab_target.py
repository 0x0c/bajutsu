"""One tab bar item to try: its center as a screen fraction, plus its readable text."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TabTarget:
    """One tab bar item to try: its center as a fraction [0,1] of the screen, plus its visible text (for logging) when readable."""

    x: float
    y: float
    label: str = ""
