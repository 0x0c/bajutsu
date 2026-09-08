"""The seam for a backend that reports the concrete actuations it performed."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .drained import Drained


@runtime_checkable
class ActuationReporter(Protocol):
    """A backend that reports the concrete actuations it performed.

    A narrow opt-in, like `ViewportProvider` / `ReadLagProvider` / `SettledReadProvider` in
    `bajutsu/common/drivers/base.py`: a backend that does not implement it simply contributes no records and
    the run is otherwise unchanged. The orchestrator drains once per step, so each step's outcome
    carries exactly the actuations that step performed.
    """

    def drain_actuations(self) -> Drained: ...
