"""How much of a crawl's discovered screen surface a run set actually reached."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .screen_ref import ScreenRef


@dataclass(frozen=True)
class ScreenCoverage:
    """How much of a crawl's discovered screen surface a run set actually reached."""

    visited: list[ScreenRef]  # discovered screens a run rendered, in fingerprint order
    unvisited: list[ScreenRef]  # discovered screens no run reached — the gap
    total: int  # discovered screens
    covered: int  # discovered screens visited
    coverage: float  # covered / total (1.0 when nothing was discovered)
