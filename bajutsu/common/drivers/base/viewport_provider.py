"""The seam for a backend that reports its true viewport, for the `scroll` stop condition (BE-0326)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ._shared import Point


@runtime_checkable
class ViewportProvider(Protocol):
    """A backend that can report its true viewport size, for the `scroll` stop condition (BE-0326).

    `scroll` stops when the target's frame center lands inside the viewport, so it needs the real
    viewport bounds — and the queried tree cannot supply them, because a lazy list keeps buffered
    off-screen rows in the tree (and the web tree keeps off-screen DOM nodes), so
    `screen_size_from_elements` overshoots the screen and would judge an off-screen center as
    on-screen. Each backend reports the real viewport its own way: Playwright via `window.innerWidth`
    / `window.innerHeight`, adb via `wm size`, XCUITest via the runner's app-window `frame`, and
    `FakeDriver` from its in-memory scrollable model. The handler falls back to
    `screen_size_from_elements` for any backend that does not implement this, so it stays a narrow
    opt-in rather than a `Driver` requirement.
    """

    # The viewport size `(w, h)`; its origin is the coordinate space's `(0, 0)`.
    def viewport(self) -> Point: ...
