"""The whole-ledger picture: totals, per-dimension breakdowns, comparison, and the daily trend."""

from __future__ import annotations

from dataclasses import dataclass, field

from .comparison_row import ComparisonRow
from .day_point import DayPoint
from .usage_row import UsageRow


@dataclass(frozen=True)
class UsageStats:
    """The whole-ledger picture: totals, per-dimension breakdowns, comparison, and the daily trend."""

    calls: int
    total_tokens: int
    total_cost: float  # sum of every priced call's cost
    priced_calls: int
    unpriced_calls: int
    period_start: str | None  # earliest event ts in the aggregated set (None when empty)
    period_end: str | None  # latest event ts
    by_provider: list[UsageRow]
    by_model: list[UsageRow]
    by_command: list[UsageRow]
    by_scenario: list[UsageRow]
    comparison: list[ComparisonRow]
    by_day: list[DayPoint] = field(default_factory=list)
