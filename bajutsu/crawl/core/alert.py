"""An OS prompt that appeared mid-crawl and was dismissed by the guard."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Alert:
    """An OS prompt that appeared mid-crawl and was dismissed by the alert guard.

    `path` is the action sequence that triggered it, `buttons` the dismiss button(s) tapped to
    clear it.
    """

    path: tuple[str, ...]
    buttons: tuple[str, ...]
