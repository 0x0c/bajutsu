"""One declared namespace the suite touches, with the referenced ids that touch it."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NamespaceCoverage:
    """One declared namespace the suite touches, with the referenced ids that touch it."""

    namespace: str
    ids: list[str]  # the distinct referenced id-strings under this namespace (sorted)
