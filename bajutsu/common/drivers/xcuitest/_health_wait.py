"""How a bounded health wait ended (BE-0360)."""

from __future__ import annotations

from enum import Enum


class _HealthWait(Enum):
    """How a bounded `/health` wait ended (BE-0360).

    Two ways to fail deserve different diagnostics, and a caller told only "the wait failed" would
    have to re-ask the liveness callback to learn which, so the wait reports which end it reached.
    """

    READY = "ready"  # the runner answered `ready` within the budget
    TIMED_OUT = "timed-out"  # the deadline passed with no `ready`
    GONE = "gone"  # the liveness callback reported the runner unable to come back
