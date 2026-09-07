"""The triage verdict for one failed scenario — a summary, a category, and suggested fixes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .fix import Fix


@dataclass(frozen=True)
class Triage:
    """The triage verdict for one failed scenario — a summary, a category, and suggested fixes."""

    summary: str
    category: str  # selector | timing | assertion | unknown
    suggestions: list[str]
    fix: Fix | None = None
