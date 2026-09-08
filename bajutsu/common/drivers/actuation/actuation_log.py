"""The actuations a driver has performed since the last drain."""

from __future__ import annotations

from collections import deque
from dataclasses import replace

from .actuation import Actuation
from .drained import Drained

# The accumulator's cap, sized well above the worst case for one drained step: a `scroll` spends up to
# `maxScrolls` gestures (default 15, author-settable with no ceiling) and an Android `tap` can add
# three more swipes bringing its target on screen. It exists for the consumers that never drain — the
# crawl, `record`'s replay, the conformance suite — which would otherwise accumulate one record per
# gesture for a whole session.
MAX_RECORDS = 512


class ActuationLog:
    """The actuations a driver has performed since the last drain.

    Bounded (see `MAX_RECORDS`) so an undraining consumer keeps the most recent records instead of
    growing with the session. Dropping is counted, not silent: the earliest gestures of a step are
    exactly what "the scroll never reached its target" needs to show.
    """

    def __init__(self, maxlen: int = MAX_RECORDS) -> None:
        self._records: deque[Actuation] = deque(maxlen=maxlen)
        self._dropped = 0

    def record(self, actuation: Actuation) -> None:
        """Append one actuation, discarding the oldest if the log is already full."""
        if len(self._records) == self._records.maxlen:
            self._dropped += 1
        self._records.append(actuation)

    def settle(self, accepted: bool) -> None:
        """Stamp the most recent record with the answer the platform just gave.

        A record is written before its transport answers, so a gesture that failed still shows what it
        aimed at. On the two channels that *can* refuse and be retried, this is how a refused attempt
        stops reading as one that landed — without it, a stale-retried tap leaves three identical
        records and nothing saying which one the device honored. A no-op on an empty log, so a driver
        that settles without having recorded cannot corrupt the previous step's last record: the drain
        already took it.
        """
        if self._records:
            self._records[-1] = replace(self._records[-1], accepted=accepted)

    def drain(self) -> Drained:
        """Everything recorded since the last drain, oldest first, emptying the log."""
        out = Drained(records=list(self._records), dropped=self._dropped)
        self._records.clear()
        self._dropped = 0
        return out
