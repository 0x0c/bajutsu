"""The whole screen map on a grid: positioned boxes, drawn edges, and the canvas size."""

from __future__ import annotations

from dataclasses import dataclass

from .box import Box
from .edge_line import EdgeLine


@dataclass(frozen=True)
class Layout:
    """The whole screen map placed on a grid: positioned boxes, drawn edges, and the canvas size."""

    boxes: list[Box]
    edges: list[EdgeLine]
    width: int
    height: int
