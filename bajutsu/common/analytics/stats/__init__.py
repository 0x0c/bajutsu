"""Aggregate the attributed AI usage/cost ledger for the serve dashboard (BE-0195).

A read-only aggregation over the JSONL ledger `bajutsu.usage_ledger` writes (one line per AI call,
tagged with provider / model / command / scenario and priced in dollars where the provider has
per-token pricing). It turns that append-only log into a picture — where the tokens and dollars go,
broken down by each dimension, compared across provider/model, and trended over time. Every figure
is an exact count or sum; there is no model and no verdict, and nothing here touches the `run` / CI
gate. It is the visualization complement to the run-stats dashboard (BE-0102), applied to a new
data source.

Cost stays honest: a subscription provider (`ant` / `claude-code`) or an unknown model records
`cost = None`, and an all-unpriced group reports its tokens with the dollar figure left absent
rather than fabricating a `$0.00`.
"""

from ._functions import _TEMPLATE_DIR as _TEMPLATE_DIR
from ._functions import _TS_DAY as _TS_DAY
from ._functions import _UNKNOWN as _UNKNOWN
from ._functions import _breakdown as _breakdown
from ._functions import _by_day as _by_day
from ._functions import _comparison as _comparison
from ._functions import _day_of as _day_of
from ._functions import _env as _env
from ._functions import _in_range as _in_range
from ._functions import _parse_ts as _parse_ts
from ._functions import aggregate_usage, render_html
from .comparison_row import ComparisonRow
from .day_point import DayPoint
from .usage_row import UsageRow
from .usage_stats import UsageStats

__all__ = ["ComparisonRow", "DayPoint", "UsageRow", "UsageStats", "aggregate_usage", "render_html"]
