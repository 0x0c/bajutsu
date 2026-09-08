"""The seam for dropping a backend's settle-proof cache from outside its own actuators."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class SettledCacheInvalidator(Protocol):
    """A backend whose settle-proof cache must be dropped by something outside its own actuators.

    `AdbDriver._settle()` caches a key proven stable so a later call can skip re-polling — but that
    proof describes a specific screen, and only the driver's own actuators (`_act`, `_device_act`,
    `type_text`) know to invalidate it when they change one. An app relaunch or a crawl reset
    replaces the screen through the platform's own launch/kill commands, never through this driver,
    so nothing would otherwise tell the cache its proof no longer applies — and if the new screen's
    projection happens to coincide with the stale one (unremarkable: many scenarios start and end on
    the same home screen), `_settle` would trust a single read of a screen it never actually proved
    at rest. A lifecycle path that replaces the screen outside the driver calls
    `invalidate_settled_cache()` to close that door too. Not implementing this means "no such cache
    to invalidate", which keeps every other backend (`FakeDriver`, Playwright, XCUITest) exactly as
    before — the same narrow opt-in as the protocols above (BE-0351).
    """

    def invalidate_settled_cache(self) -> None: ...
