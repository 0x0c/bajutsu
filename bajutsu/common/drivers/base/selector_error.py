"""The base error for a selector that could not be resolved."""

from __future__ import annotations

# --- Selector resolution (the determinism core) ---


class SelectorError(Exception):
    """Selector resolution failed."""
