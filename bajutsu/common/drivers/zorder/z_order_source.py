"""The seam a driver reads measured z-order positions through, or nothing."""

from __future__ import annotations

from typing import Protocol


class ZOrderSource(Protocol):
    """What a driver needs of the responder: identifier to measured position, or nothing."""

    def positions(self) -> dict[str, float]: ...
