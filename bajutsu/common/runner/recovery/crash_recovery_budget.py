"""The count and wall-clock retry decision for one unit of recoverable work."""

from __future__ import annotations

from collections.abc import Callable

from .retry_decision import RetryDecision


class CrashRecoveryBudget:
    """The count + wall-clock retry decision for one unit of recoverable work (a scenario, a test).

    Construct one per unit of work (its wall-clock deadline is per-unit state), then call `on_crash`
    with the 1-based attempt number each time that unit's backend crashes. The budget itself performs
    no leasing or respawning — it only decides whether the caller's respawn loop should continue — so
    the pipeline and the conformance harness share the *decision* while each keeps its own loop and
    failure prose.
    """

    def __init__(self, retries: int, budget: float | None, now: Callable[[], float]) -> None:
        self._retries = retries
        self._budget = budget
        self._now = now
        # Set lazily at the first crash so the first respawn is never blocked by the budget.
        self._deadline: float | None = None

    @property
    def total_attempts(self) -> int:
        """The initial attempt plus every respawn the count allows (`retries + 1`)."""
        return self._retries + 1

    def on_crash(self, attempt: int) -> RetryDecision:
        """Record a crash on the 1-based `attempt` and decide whether another respawn is allowed."""
        # Capture the clock once so both deadline initialisation and the budget check see the same
        # instant — a double call could in theory advance past a tiny budget between the two reads.
        t = self._now()
        # Start the recovery clock at the first crash: `t < deadline` holds here, so the first
        # respawn always proceeds; the budget can only stop a *later* respawn once earlier ones have
        # burned the wall-clock (a slow, never-recovering runner).
        if self._budget is not None and self._deadline is None:
            self._deadline = t + self._budget
        within_count = attempt <= self._retries
        within_budget = self._deadline is None or t < self._deadline
        # The count would allow another respawn but the wall-clock budget is spent: a distinct end
        # state from "attempts exhausted", which the caller surfaces in its failure message.
        return RetryDecision(
            will_retry=within_count and within_budget,
            budget_spent=within_count and not within_budget,
        )
