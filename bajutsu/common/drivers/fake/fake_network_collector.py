"""A deterministic in-process network collector over a fixed exchange list (BE-0020)."""

from __future__ import annotations

import time

from bajutsu.common.evidence.network import NetworkExchange, ScreenTransition


class FakeNetworkCollector:
    """A deterministic in-process `network.Collector` over a fixed exchange list (BE-0020 tests).

    Real test data, not a behavior mock: it just replays the exchanges it was seeded with, so a
    network-capable fallback can be exercised end to end on the Linux gate without a device.
    """

    def __init__(self, exchanges: list[NetworkExchange]) -> None:
        now = time.monotonic()
        self._items: list[tuple[NetworkExchange, float]] = [(ex, now) for ex in exchanges]

    def snapshot(self) -> list[NetworkExchange]:
        return [ex for ex, _ in self._items]

    def snapshot_timed(self) -> list[tuple[NetworkExchange, float]]:
        return list(self._items)

    def transitions_snapshot_timed(self) -> list[tuple[ScreenTransition, float]]:
        return []  # the fake driver seeds no screen-transition events (BE-0310)

    def clear(self) -> None:
        self._items.clear()

    def stop(self) -> None:
        pass  # nothing to release
