"""The error raised when a uniquely resolved element cannot be reached at its own point."""

from __future__ import annotations


class ElementNotTappable(Exception):
    """The selector resolved uniquely, but the element could not be reached at its own point.

    Obstructed by another on-screen element, or the platform's own hit-test refused it — even
    after the bounded scroll safety net tried to clear the obstruction. Distinct from
    `SelectorError`: resolution succeeded. Only reachability failed.
    """
