"""The error raised when no candidate matched a selector."""

from __future__ import annotations

from .selector_error import SelectorError


class ElementNotFound(SelectorError):
    """No candidate matched. A wait times out; an immediate action fails."""
