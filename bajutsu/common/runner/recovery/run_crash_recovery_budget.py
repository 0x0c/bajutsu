"""The wall-clock ceiling on recovery time accumulated across a whole run."""

from __future__ import annotations

import threading


class RunCrashRecoveryBudget:
    """Wall-clock ceiling on *actual recovery time* accumulated across a whole run, not one scenario.

    `CrashRecoveryBudget` resets a fresh deadline for every scenario, so a device that keeps
    degrading pays each scenario's own budget again — this class shares one accumulator across every
    scenario in a run instead. It bills only the time a scenario's own crash-retry loop actually
    spends recovering (`bajutsu/common/runner/pipeline.py`'s `run_one` times its own retry loop and reports
    the elapsed seconds via `add_recovery_time`), not wall-clock elapsed since some earlier crash: an
    earlier design armed a single deadline at the first crash and never re-armed it, so a long,
    perfectly healthy stretch between two unrelated one-off crashes silently ate into the same
    budget, and a scenario whose backend crashed only once, late in the run, could be denied even its
    first retry — exactly the "residual one-off crash" `crash_retries` exists to ride out. Billing
    the accumulated total instead means 600s means 600s actually spent recovering.

    Deliberately keeps no notion of an in-progress "episode" as shared state: `run_all`'s
    `workers > 1` path can run several scenarios' crash-retry loops concurrently
    (`bajutsu/common/runner/pool.py`'s `lease_defect_lock` guards shared state across that same
    `ThreadPoolExecutor` for the same reason this class needs a lock), and a single shared
    start-of-episode timestamp would let two concurrent recoveries corrupt each other's timing —
    whichever finished first would end "the" episode out from under the other. Each `run_one` call
    times its own loop with a local variable instead (never shared), and only ever calls into this
    class for a threadsafe read (`exhausted`) or a single atomic add (`add_recovery_time`) once its
    own loop is done — so accumulation is correct under any amount of concurrency. Note what the
    total measures, though: a *sum of per-scenario recovery seconds*, not elapsed wall-clock. Under
    `run_all`'s `workers > 1` path, N scenarios recovering at once bill N x the real time, so a
    parallel lane must size its budget against `workers x` the serial figure or it exhausts that
    much sooner and denies a later scenario even its first retry.

    `budget` is public (not `_budget`) so a caller that needs the configured seconds for a failure
    message (`bajutsu/common/runner/pipeline.py`'s `run_one`) reads it straight from the one object that
    also enforces it, rather than keeping a second field of its own in sync by hand.

    `exhausted()` alone is a weaker signal than it looks: the accumulated total bills recovery time
    regardless of outcome (`add_recovery_time` runs whether the scenario that just recovered went on
    to pass or ultimately failed), so it can cross the budget from a single recovery that *succeeded*
    — a device that took a long time to come back but is now healthy.
    `given_up_cause()`/`mark_given_up()` track the stronger signal a caller needs before refusing
    every later scenario a first attempt: recovery has actually been abandoned for this run, either
    because a scenario's own crash-retry loop ended in failure *because* this budget, specifically,
    was the binding constraint, or because a device preparation timed out (BE-0374). Only that — not
    mere exhaustion — is real evidence the device itself is not going to recover.

    The latch outgrew this class's name once a timeout could set it, and it keeps living here anyway
    rather than moving to a second object — see BE-0374's *Alternatives considered* for why.
    """

    def __init__(self, budget: float | None) -> None:
        # Non-positive reads as unbounded, the same way `_default_run_crash_recovery_budget` reads
        # `BAJUTSU_RUN_CRASH_RECOVERY_BUDGET=0` — so a caller pinning the budget directly can never
        # invert the never-block-the-first-crash rule `exhausted()` documents below.
        self.budget = budget if budget is None or budget > 0 else None
        self._spent = 0.0
        self._given_up_cause: str | None = None
        self._lock = threading.Lock()

    def exhausted(self) -> bool:
        """Whether the accumulated recovery time already meets the budget. Always `False` when unbounded.

        A budget of exactly 0 seconds accumulated never exhausts a positive budget (`_default_run_crash_recovery_budget`
        never returns a non-positive value, so this only ever compares a real elapsed total against a
        real ceiling) — the run's very first crash always sees `_spent == 0.0`, so it is never blocked
        by this check alone. Says nothing about whether the device can still recover — see the class
        docstring — so a caller deciding whether to skip a *future* scenario's first attempt should
        read `given_up_cause()` instead.
        """
        with self._lock:
            return self.budget is not None and self._spent >= self.budget

    def given_up_cause(self) -> str | None:
        """Why crash recovery was abandoned for this run, or None while it has not been.

        The signal that later scenarios should stop paying their own first attempt against the same
        device, unlike bare `exhausted()`, which a successful-but-slow recovery can also trip. It
        answers with the *cause* rather than a bare yes, because a latch has two of them and the
        difference is visible to an operator: this budget being the binding constraint, or a device
        preparation that timed out on a wedged host (BE-0374). Reporting the budget for a run that
        never had one was not merely misleading but a defect — `BAJUTSU_RUN_CRASH_RECOVERY_BUDGET` is
        unset by default, so formatting `budget` into the message raised a `TypeError` out of
        `run_one` and discarded every verdict the run had earned.
        """
        with self._lock:
            return self._given_up_cause

    def mark_given_up(self, cause: str) -> None:
        """Record that crash recovery has been abandoned for this run, and why — once.

        `cause` is the phrase `given_up_cause`'s consumers read back into a failure message, so it
        reads as the middle of one ("... skipped: <cause>, so this scenario was never leased") and
        must be a non-empty phrase rather than a full sentence of its own. Called from the two places
        `run_one` determines it: the `run_budget_spent` failure branch, and a device preparation that
        timed out. Never on a recovery that succeeded.

        The first call wins; a later one is a no-op. `run_all`'s `workers > 1` path can run several
        scenarios' crash-retry loops concurrently, so two could abandon recovery for different
        reasons within the same window — write-once keeps the reported cause the one that actually
        established the latch, rather than whichever call happened to land last.
        """
        if not cause:
            raise ValueError(
                "a latch cause must be a non-empty phrase — it is read into a failure message"
            )
        with self._lock:
            if self._given_up_cause is None:
                self._given_up_cause = cause

    def add_recovery_time(self, seconds: float) -> None:
        """Bill `seconds` of actual recovery time against the shared run-level total.

        Called once per scenario whose backend crashed at least once, after its own crash-retry loop
        ends (pass or fail) — a scenario that never crashes never calls this, so the common case costs
        no lock acquisition at all.
        """
        with self._lock:
            self._spent += seconds
