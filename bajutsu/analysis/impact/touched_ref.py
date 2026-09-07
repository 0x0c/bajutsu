from __future__ import annotations

from dataclasses import dataclass

from .reference import Reference


@dataclass(frozen=True, order=True)
class TouchedRef:
    """A referenced literal the diff touched, with the changed files whose lines carry it."""

    reference: Reference
    files: list[str]
