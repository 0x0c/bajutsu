"""The seam for a backend whose read can describe the screen before the last actuation."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ReadLagProvider(Protocol):
    """A backend whose `query()` can describe the screen as it was *before* the last actuation.

    Most backends read synchronously enough that a fresh `query()` already reflects the action just
    performed, so `scroll` can treat one unchanged region as proof the content stopped. Android breaks
    that assumption: the gesture moves the list, and the accessibility update naming the new frames is
    published afterwards, so a read taken in between returns the pre-scroll tree even though the
    content has already moved. Left unhandled, that late tree becomes a spurious "end of content"
    failure.

    A backend that can lag reports the budget `scroll` should give a step's result before concluding
    the region really stopped. Not implementing this means "my reads do not lag", which keeps the
    end-of-content failure immediate — so the fast, synchronous backends (`FakeDriver`, Playwright,
    XCUITest) pay nothing and stay exactly as fail-fast as before. A narrow opt-in, like
    `ViewportProvider` above, rather than a `Driver` requirement.
    """

    # Seconds to wait for a read to catch up with the last actuation; only ever spent when the region
    # looks unchanged, and never on the path where the step visibly landed.
    def read_lag(self) -> float: ...
