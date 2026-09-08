"""The slice of Playwright's keyboard the driver's text entry is expressed through."""

from __future__ import annotations

from typing import Protocol


class _Keyboard(Protocol):
    def type(self, text: str) -> None:
        pass

    def press(self, key: str) -> None:
        pass
