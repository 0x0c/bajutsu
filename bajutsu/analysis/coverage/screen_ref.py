"""A screen a crawl discovered, named by its fingerprint and a human-readable label."""

from __future__ import annotations

from dataclasses import dataclass

# --- screens-visited: screens a crawl discovered vs the screens a run set actually reached ---


@dataclass(frozen=True)
class ScreenRef:
    """A discovered screen: its crawl fingerprint and a human label (its first id, or short hash)."""

    fingerprint: str
    label: str
