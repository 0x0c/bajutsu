from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class Reference:
    """A literal a change can touch: a stable id, a screen name/deeplink, or an asserted endpoint."""

    kind: str  # "id" | "screen" | "endpoint"
    value: str
