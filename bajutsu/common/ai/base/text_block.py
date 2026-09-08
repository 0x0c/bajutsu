"""A text block in a normalized model response."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TextBlock:
    """A text block in a model response."""

    text: str
