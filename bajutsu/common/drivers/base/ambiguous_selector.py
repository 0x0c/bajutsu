"""The error raised when a selector matched several elements — never a tap on the first."""

from __future__ import annotations

from .selector_error import SelectorError


class AmbiguousSelector(SelectorError):
    """2+ candidates with no way to disambiguate; needs `within` or `index`."""
