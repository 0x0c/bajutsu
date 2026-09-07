"""One conversation message in a normalized turn."""

from __future__ import annotations

from dataclasses import dataclass

from .image_part import ImagePart
from .text_part import TextPart

ContentPart = TextPart | ImagePart


@dataclass(frozen=True)
class Message:
    """One conversation message. Every current path sends a single ``user`` message."""

    role: str
    content: list[ContentPart]
