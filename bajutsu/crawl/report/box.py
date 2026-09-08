"""One screen laid out on the report's grid: its position and what its card shows."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Box:
    """One screen laid out on the grid: its position and the bits the card shows."""

    fp: str
    kind: str
    ids: tuple[str, ...]
    actions: tuple[str, ...]
    x: int
    y: int
    has_shot: bool
