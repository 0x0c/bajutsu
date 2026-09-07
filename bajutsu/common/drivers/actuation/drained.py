"""One drain's records, plus what the cap discarded to make room for them."""

from __future__ import annotations

from dataclasses import dataclass

from .actuation import Actuation


@dataclass(frozen=True)
class Drained:
    """One drain's worth of records, plus what the cap discarded to make room for them.

    `dropped` travels with the records rather than staying a log-side counter so a truncated record
    can be *disclosed as truncated* wherever it is shown. A warning line would not do: this item's own
    reasoning for existing is that a log line is not evidence — absent unless someone raised the level
    before the run, and it never reaches the run directory.
    """

    records: list[Actuation]
    dropped: int
