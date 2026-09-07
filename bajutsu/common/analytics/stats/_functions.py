"""Aggregate ledger events into the usage and cost picture the dashboard renders (BE-0195)."""

from __future__ import annotations

import functools
import re
from collections import Counter
from collections.abc import Callable, Iterable
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from bajutsu.common.analytics.ledger import UsageEvent

from .comparison_row import ComparisonRow
from .day_point import DayPoint
from .usage_row import UsageRow
from .usage_stats import UsageStats

# A ledger timestamp is a UTC ISO-8601 string (`datetime.now(UTC).isoformat()`), so the day is the
# leading `YYYY-MM-DD`; a line whose ts doesn't start that way simply has no day and buckets under "".
_TS_DAY = re.compile(r"^(\d{4}-\d{2}-\d{2})")

_UNKNOWN = "(unknown)"


# The shared Jinja templates live at the package root (`bajutsu/templates/`), two levels up now
# that this module is packaged under `common/analytics/` (BE-0257; nested under `common/` per the
# feature-first reorg).
_TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "templates"


def aggregate_usage(
    events: Iterable[UsageEvent],
    *,
    since: datetime | None = None,
    until: datetime | None = None,
) -> UsageStats:
    """Aggregate ledger events into the usage/cost picture the dashboard renders (BE-0195).

    Pure and observational: it counts and sums the recorded events only — no device, no network, no
    model, and it never re-prices or changes a figure. An unpriced call (`cost=None`) contributes its
    tokens but no dollars, and both a `since` and an `until` (inclusive-exclusive on the event's UTC
    timestamp) narrow the set before every aggregate is computed.

    Args:
        events: The ledger's `UsageEvent`s, in any order.
        since: Keep only events at or after this instant; None leaves the lower bound open.
        until: Keep only events strictly before this instant; None leaves the upper bound open.

    Returns:
        The `UsageStats`: totals, the per-provider / model / command / scenario breakdowns (each
        ranked by descending calls), the per-(provider, model) efficiency comparison, and the daily
        trend (chronological).
    """
    kept = [e for e in events if _in_range(e, since, until)]

    total_tokens = sum(e.usage.total_tokens for e in kept)
    priced = [e for e in kept if e.cost is not None]
    return UsageStats(
        calls=len(kept),
        total_tokens=total_tokens,
        total_cost=sum(e.cost or 0.0 for e in priced),
        priced_calls=len(priced),
        unpriced_calls=len(kept) - len(priced),
        period_start=min((e.ts for e in kept), default=None),
        period_end=max((e.ts for e in kept), default=None),
        by_provider=_breakdown(kept, lambda e: e.provider),
        by_model=_breakdown(kept, lambda e: e.model),
        by_command=_breakdown(kept, lambda e: e.command),
        by_scenario=_breakdown(kept, lambda e: e.scenario),
        comparison=_comparison(kept),
        by_day=_by_day(kept),
    )


def _in_range(event: UsageEvent, since: datetime | None, until: datetime | None) -> bool:
    """Whether *event* falls in [since, until); a parse-less ts is excluded only when a bound is set."""
    if since is None and until is None:
        return True
    ts = _parse_ts(event.ts)
    if ts is None:
        return False  # a bound is active but the ts is unplaceable — can't include it
    if since is not None and ts < since:
        return False
    return not (until is not None and ts >= until)


def _parse_ts(ts: str) -> datetime | None:
    """The event's timestamp as an aware datetime, or None when it isn't a usable ISO-8601 instant.

    The ledger always writes a UTC offset, so an offset-naive line is malformed; treat it as
    unplaceable (None) rather than return a naive datetime that would raise `TypeError` when compared
    against the aware `since` / `until` bounds in `_in_range` — one bad line must not crash the filter.
    """
    try:
        parsed = datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        return None
    return parsed if parsed.tzinfo is not None else None


def _breakdown(events: list[UsageEvent], key: Callable[[UsageEvent], str | None]) -> list[UsageRow]:
    """Group *events* by one dimension into rows ranked by descending calls, then key for stability."""
    calls: Counter[str] = Counter()
    tokens: Counter[str] = Counter()
    cost: dict[str, float] = {}
    priced: Counter[str] = Counter()
    for e in events:
        k = key(e) or _UNKNOWN
        calls[k] += 1
        tokens[k] += e.usage.total_tokens
        if e.cost is not None:
            cost[k] = cost.get(k, 0.0) + e.cost
            priced[k] += 1
    rows = [
        UsageRow(
            key=k,
            calls=calls[k],
            tokens=tokens[k],
            cost=cost.get(k, 0.0),
            priced_calls=priced[k],
            unpriced_calls=calls[k] - priced[k],
        )
        for k in calls
    ]
    rows.sort(key=lambda r: (-r.calls, r.key))
    return rows


def _comparison(events: list[UsageEvent]) -> list[ComparisonRow]:
    """Per-(provider, model) efficiency, ranked by descending cost then calls (unpriced last)."""
    calls: Counter[tuple[str, str]] = Counter()
    tokens: Counter[tuple[str, str]] = Counter()
    cost: dict[tuple[str, str], float] = {}
    priced: Counter[tuple[str, str]] = Counter()
    scenarios: dict[tuple[str, str], set[str]] = {}
    for e in events:
        pair = (e.provider or _UNKNOWN, e.model or _UNKNOWN)
        calls[pair] += 1
        tokens[pair] += e.usage.total_tokens
        scenarios.setdefault(pair, set()).add(e.scenario or _UNKNOWN)
        if e.cost is not None:
            cost[pair] = cost.get(pair, 0.0) + e.cost
            priced[pair] += 1
    rows = []
    for pair in calls:
        pair_cost = cost.get(pair, 0.0)
        pair_priced = priced[pair]
        pair_scenarios = len(scenarios[pair])
        rows.append(
            ComparisonRow(
                provider=pair[0],
                model=pair[1],
                calls=calls[pair],
                scenarios=pair_scenarios,
                tokens=tokens[pair],
                cost=pair_cost,
                priced_calls=pair_priced,
                # None (not $0.00) when the pair has no priced call — an unpriced pair has no dollar
                # efficiency to compare on, only tokens.
                cost_per_call=pair_cost / pair_priced if pair_priced else None,
                cost_per_scenario=pair_cost / pair_scenarios if pair_priced else None,
            )
        )
    # Unpriced pairs (no priced call) always sort last — a priced pair whose cost happens to sum to
    # $0.00 still ranks above them — then by descending cost, then calls, then the key for stability.
    rows.sort(key=lambda r: (r.priced_calls == 0, -r.cost, -r.calls, r.provider, r.model))
    return rows


def _by_day(events: list[UsageEvent]) -> list[DayPoint]:
    """Roll events up into per-day calls / tokens / cost, oldest day first."""
    calls: Counter[str] = Counter()
    tokens: Counter[str] = Counter()
    cost: dict[str, float] = {}
    for e in events:
        day = _day_of(e.ts)
        calls[day] += 1
        tokens[day] += e.usage.total_tokens
        if e.cost is not None:
            cost[day] = cost.get(day, 0.0) + e.cost
    return [
        DayPoint(day=day, calls=calls[day], tokens=tokens[day], cost=cost.get(day, 0.0))
        for day in sorted(calls)
    ]


def _day_of(ts: str) -> str:
    """The `YYYY-MM-DD` a ledger ts opens with, or "" when it carries no date prefix."""
    match = _TS_DAY.match(ts)
    return match.group(1) if match else ""


@functools.lru_cache(maxsize=1)
def _env() -> Environment:
    # autoescape so a stray "<" in a scenario name or model id can never inject markup into the page.
    return Environment(loader=FileSystemLoader(str(_TEMPLATE_DIR)), autoescape=True)


def render_html(s: UsageStats) -> str:
    """A self-contained HTML dashboard (inline CSS, minimal inline SVG, no JS, no external asset).

    Headline totals, the per-dimension breakdowns, the provider/model comparison, and the daily
    trend on one page. Read-only and AI-free, mirroring the run-stats dashboard (BE-0102).
    """
    return _env().get_template("usage.html.j2").render(stats=s)
