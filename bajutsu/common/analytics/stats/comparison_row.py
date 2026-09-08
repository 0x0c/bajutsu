"""One provider-and-model pair's efficiency, the view that serves the optimization goal."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ComparisonRow:
    """One (provider, model) pair's efficiency — the view that serves the optimization goal.

    `cost_per_call` / `cost_per_scenario` are None when the pair has no priced call, so an unpriced
    subscription model is compared on tokens without an invented dollar efficiency.
    """

    provider: str
    model: str
    calls: int
    scenarios: int  # distinct scenarios this pair was spent on
    tokens: int
    cost: float
    priced_calls: int
    cost_per_call: float | None
    cost_per_scenario: float | None
