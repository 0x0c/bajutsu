"""A touchscreen `/dev/input` node and its raw coordinate range, read from `getevent -lp`."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TouchDevice:
    """A touchscreen `/dev/input` node and its raw coordinate range, from `getevent -lp`."""

    path: str
    max_x: int
    max_y: int
