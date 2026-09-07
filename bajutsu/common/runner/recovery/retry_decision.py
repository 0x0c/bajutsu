"""How recording one crash came out: whether to respawn, and why recovery would stop."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RetryDecision:
    """The outcome of recording one crash: whether to respawn, and why recovery would stop.

    `budget_spent` distinguishes "the wall-clock budget ran out while the count still allowed a
    respawn" from "the retry count is exhausted", so the caller can report the honest end state.
    """

    will_retry: bool
    budget_spent: bool
