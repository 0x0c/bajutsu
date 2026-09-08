"""What a between-attempts recovery did, and whether the next attempt earned a fresh budget."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class _Recovery:
    """What a between-attempts recovery did, and whether the next attempt has earned a fresh budget.

    `note` goes into the failing error's diagnostics, so a reader sees which rung ran and what the
    device looked like. `fresh_budget` is the repaired device's new readiness ceiling in seconds, or
    `None` when nothing about the device changed — the difference between "retry against a device we
    just rebooted" and "retry against the same device", which is what decides whether a second full
    wait is justified.
    """

    note: str
    fresh_budget: float | None = None
