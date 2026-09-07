"""The slice of Playwright's mouse the driver's gestures are synthesized from."""

from __future__ import annotations

from typing import Protocol


# The subset of Playwright's Page the driver uses — kept as a Protocol so tests can inject a
# fake page without importing playwright, and the real (untyped, lazily imported) page satisfies it.
class _Mouse(Protocol):
    def click(self, x: float, y: float) -> None:
        pass

    def dblclick(self, x: float, y: float) -> None:
        pass

    def move(self, x: float, y: float) -> None:
        pass

    def down(self) -> None:
        pass

    def up(self) -> None:
        pass

    def wheel(self, delta_x: float, delta_y: float) -> None:
        pass
