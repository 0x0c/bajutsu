"""The seam for a backend that can order its last read against the last actuation (BE-0332)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ReadOrderProvider(Protocol):
    """A backend that can tell whether its last `query()` postdates the last actuation (BE-0332 Unit 3).

    `ReadLagProvider` above bounds the wait for a lagging read with a wall-clock budget; this answers
    the ordering question directly. Android's resident reader stamps each read with the device-clock
    time of the most recent accessibility event it has seen, and the driver takes a device-clock mark
    before each gesture, so it knows the moment a read reflects device state *after* the action — no
    host-to-device clock skew, because both marks are the device's.

    No production caller reads this through the protocol today. The `extract` poll used to release
    early on a confirmed order, until that release was found to accept a stale value — the mark says
    an accessibility event postdates the gesture, not that the property being copied out has been
    republished — so `extract` now keeps its wall-clock budget unconditionally. The driver's own
    catch-up barrier is the remaining ordering consumer, and it reads the backend's device mark
    directly rather than through here. The protocol stays declared because the driver conformance
    suite (BE-0114) checks the marked-read contract against the real backend, and because narrowing
    the barrier to the reads that still need it is an open unit of the device-side actuation item — a
    live contract without a live caller, not a leftover. A backend that cannot answer simply does not
    implement it, and every poll keeps its wall-clock budget unchanged — the same narrow opt-in as
    `ReadLagProvider` and `ViewportProvider`.
    """

    # Whether a read has positively postdated the last actuation, confirmed by the backend's device
    # mark. True only on that confirmation, and reset by the next actuation — deliberately not merely
    # "nothing is pending", so an actuation the backend could not mark (no device event, a stale-tree
    # timeout, a channel without the mark) reads false.
    def read_postdates_actuation(self) -> bool: ...
