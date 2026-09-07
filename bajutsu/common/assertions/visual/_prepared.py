"""Visual preprocessing's result: what to compare, plus the frame data later steps reuse."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bajutsu.common.scenario import ExcludeRegion


@dataclass(frozen=True)
class _Prepared:
    """The result of visual preprocessing: what to compare, plus the frame data later steps reuse.

    `compare_actual` is the image handed to the compare engine (the element crop when scoped, else
    the whole screenshot); `actual_rel` is its run-dir-relative path for the evidence. `crop` and
    `scale` are None for a whole-screen comparison and set once frames were resolved.
    """

    compare_actual: Path
    actual_rel: str
    crop: ExcludeRegion | None
    scale: tuple[float, float] | None
