from __future__ import annotations

from dataclasses import dataclass

from .affected_step import AffectedStep
from .touched_ref import TouchedRef


@dataclass(frozen=True)
class Impact:
    """The affected steps a change selects, plus the soundness signal a CI narrowing must respect."""

    affected: list[AffectedStep]  # steps a touched reference points at, sorted
    touched: list[TouchedRef]  # the referenced literals the diff touched, sorted
    unattributable: list[str]  # changed files that touched no referenced literal (sorted, de-duped)
    complete: (
        bool  # no unattributable change — else a full run is warranted (conservative fallback)
    )
