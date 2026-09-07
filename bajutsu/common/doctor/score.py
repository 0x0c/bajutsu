"""The current screen's accessibility-convention score: id coverage, conformance, and grade."""

from __future__ import annotations

from dataclasses import dataclass

from bajutsu.common.drivers import base


@dataclass(frozen=True)
class Score:
    """The current screen's accessibility-convention score — id coverage, conformance, and grade."""

    actionable: int
    with_id: int
    id_coverage: float
    namespace_conformance: float
    duplicate_ids: int
    grade: str  # "Ready" | "Partial" | "Blocked"
    # Nothing actionable on the screen (likely blank / not loaded / wrong screen).
    no_actionable: bool
    missing_id: list[base.Element]  # actionable elements without an id
    off_namespace: list[str]  # ids whose first segment is not a declared namespace
    duplicates: list[str]  # ids that appear 2+ times on the screen
