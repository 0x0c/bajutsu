"""An alert that interrupted an interaction and matched no declared rule."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class UndeclaredInterruption:
    """An alert that interrupted an XCUITest interaction and matched no `rules` entry.

    XCUITest answers it with the alert's own default button regardless — nothing here changes that
    tap, and it is never reported as an `AlertEvent`, since nothing was answered on the scenario's
    behalf. Recording it is what lets the step or `expect` that met it fail by name instead of
    reading as an unrelated pass or an unexplained assertion mismatch (BE-0406 Unit 2b)."""

    buttons: list[str] = field(default_factory=list)
