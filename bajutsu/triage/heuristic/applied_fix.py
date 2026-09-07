"""A fix already applied to scenario source, packaged for a UI to preview and write back (BE-0147)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AppliedFix:
    """A fix applied to scenario source, packaged for a UI to preview and write back (BE-0147).

    `patched` is the full source with the fix applied; `diff` is its unified diff — empty when
    `count` is 0 (the fragment no longer matches the source, a safe no-op the diff makes obvious).
    """

    path: str
    count: int
    diff: str
    patched: str
