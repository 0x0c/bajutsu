"""The seam for a backend whose reads must settle before a coordinate is taken from one."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .element import Element


@runtime_checkable
class SettledReadProvider(Protocol):
    """A backend whose reads need settling before a coordinate is resolved from one for actuation.

    Every selector-addressed actuator the adb driver owns — `tap`, `double_tap`, `long_press`,
    `pinch`, `rotate` — resolves its target through the driver's own settle, which waits out the
    catch-up barrier so the frame a touch aims at comes from a tree the device published after the
    previous gesture. A directional `swipe` and a `drag` cannot: their endpoints are computed above
    the driver (`_directional_endpoints`), which only has `query()` to work with, and the driver
    receives two coordinates that no longer name an element. One unbarriered read there is enough to
    anchor a pan on the previous screen's frames — the failure mode `ReadLagProvider` above describes,
    reached by the one door the barrier does not cover.

    A backend that needs the settle exposes it here, so the handler can ask for an actuation-grade
    read rather than a bare one. Not implementing this means "a single `query()` is already good
    enough to actuate from", which keeps the synchronous backends (`FakeDriver`, Playwright,
    XCUITest) on exactly the read they take today. A narrow opt-in, like the three protocols above,
    rather than a `Driver` requirement.
    """

    # A tree fit to resolve an actuation target from: settled, and past any pending read-lag barrier.
    def settled_query(self) -> list[Element]: ...
