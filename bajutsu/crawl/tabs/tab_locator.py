"""The seam that finds a screen's tab bar items, or reports there is none."""

from __future__ import annotations

from typing import Protocol

from .tab_target import TabTarget


class TabLocator(Protocol):
    """Given a screenshot, return the tab bar's items (empty when there is no addressable tab bar)."""

    def locate(self, screenshot_png: bytes) -> list[TabTarget]: ...
