"""The exchange source the run loop and the evidence writer drive."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .network_exchange import NetworkExchange
from .screen_transition import ScreenTransition


@runtime_checkable
class Collector(Protocol):
    """The exchange source the run loop and evidence writer drive.

    Independent of how it observed the traffic: the iOS `NetworkCollector` receives POSTs over HTTP;
    the web `WebNetworkCollector` hooks Playwright events — both satisfy this, so the pipeline stays
    backend-agnostic.
    """

    def snapshot(self) -> list[NetworkExchange]: ...  # observed exchanges, in arrival order
    def snapshot_timed(self) -> list[tuple[NetworkExchange, float]]: ...  # each + receive time
    def clear(self) -> None: ...  # drop observed exchanges (scoped per scenario by the run loop)
    def stop(self) -> None: ...  # release the observation resource (HTTP receiver / event hooks)
    # Screen-transition events (BE-0310), each with its receive time; independent of the exchanges
    # above. A collector with no such observer (web, fake) returns an empty list.
    def transitions_snapshot_timed(self) -> list[tuple[ScreenTransition, float]]: ...
