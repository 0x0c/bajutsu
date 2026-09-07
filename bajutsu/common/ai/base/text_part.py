"""The text part of a user message."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TextPart:
    """A text part of a user message."""

    text: str
