"""Throttled "still waiting" lines, so a pending wait shows what it is waiting on."""

from __future__ import annotations

from dataclasses import dataclass

from ._shared import WaitTick

# Min seconds between live "still waiting …" lines. Waits poll every _POLL (50ms); a per-poll
# progress line would flood the run log, so the heartbeat below throttles it to a readable cadence.
# 5s keeps the countdown legible rather than a per-second scroll.
_TICK_INTERVAL = 5.0


@dataclass
class _Heartbeat:
    """Throttled emitter of "still waiting …" lines so a pending wait shows what it awaits.

    Purely a display aid, fed the poll clock via `tick`: it never reads the tree or influences the
    wait's pass/fail (prime directive 1). The first `tick` always fires, so even a wait that resolves
    on its first poll surfaces its condition once; later ticks are spaced by `_TICK_INTERVAL`.
    """

    emit: WaitTick
    deadline: float
    _next: float = 0.0  # clock time of the next allowed emit; 0 => fire on the first tick

    def tick(self, now: float) -> None:
        if now >= self._next:
            self._next = now + _TICK_INTERVAL
            self.emit(max(0.0, self.deadline - now))
