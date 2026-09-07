"""A mechanically-applicable scenario edit a human reviews before it is written."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Fix:
    """A mechanically-applicable edit a human reviews before it is written (`find` -> `replace`).

    Applied over the scenario source.
    `renameId` replaces a selector id as a whole token (safe to apply everywhere it appears —
    the classic self-heal). `addIndex` / `raiseTimeout` replace an exact fragment of the
    failing step (disambiguate an ambiguous match, or lengthen a wait). The boundary still
    holds: every fix is shown as a diff and written only when the human opts in, and a fragment
    that no longer matches the source is a safe no-op.
    """

    kind: str  # one of FIX_KINDS
    summary: str
    find: str
    replace: str
