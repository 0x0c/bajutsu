"""Read a provider's usage object into neutral counts, and record it against the tracker."""

from __future__ import annotations

import contextlib
from typing import Any

from ._accumulator import _Accumulator
from ._shared import CATEGORY_ACTION, CATEGORY_ALERT, CATEGORY_OTHER, CATEGORY_PLAN
from .token_usage import TokenUsage

_TRACKER = _Accumulator()


# Categories listed in this order in the breakdown (known ones first, then any extra), so the report
# reads plan → per-turn actions → alert guard rather than dict-insertion order.
_CATEGORY_ORDER = (CATEGORY_PLAN, CATEGORY_ACTION, CATEGORY_ALERT, CATEGORY_OTHER)


def _int(value: Any) -> int:
    """A token count coerced to a non-negative int; anything unexpected counts as zero."""
    return int(value) if isinstance(value, (int, float)) and value > 0 else 0


def _field(usage: Any, name: str) -> int:
    """One token field, read from an SDK usage object *or* a plain dict (the Claude Code adapter's
    envelope reports usage as a dict — BE-0176 — so attribute-only access would count it as zero)."""
    raw = usage.get(name) if isinstance(usage, dict) else getattr(usage, name, 0)
    return _int(raw)


def of(usage: Any) -> TokenUsage:
    """One response's counts as a `TokenUsage` (``calls=1`` when usage is present), for per-call
    display. Best-effort like `record`: a ``None`` usage yields an empty (zero) snapshot."""
    if usage is None:
        return TokenUsage()
    return TokenUsage(
        input_tokens=_field(usage, "input_tokens"),
        output_tokens=_field(usage, "output_tokens"),
        cache_write_tokens=_field(usage, "cache_creation_input_tokens"),
        cache_read_tokens=_field(usage, "cache_read_input_tokens"),
        calls=1,
    )


def record(
    usage: Any,
    category: str = CATEGORY_OTHER,
    *,
    provider: str | None = None,
    model: str | None = None,
) -> None:
    """Record one provider response's `usage` into the process-global tracker under `category`.

    Provider-agnostic (BE-0104): the `usage` object comes from whichever backend answered — the
    Anthropic SDK, Bedrock, or the `claude-code` CLI's dict envelope. When a ledger is configured
    (BE-0196), also append one attributed, priced event; *provider* and *model* name what produced
    the tokens. Ledger emission is best-effort and never raises — a broken sink must not break the AI
    path — and never touches the deterministic verdict.
    """
    _TRACKER.record(usage, category)
    _emit_ledger_event(usage, provider=provider, model=model)


def _emit_ledger_event(usage: Any, *, provider: str | None, model: str | None) -> None:
    """Forward the usage to the ledger, swallowing anything it raises (reporting only, BE-0196).

    Imported lazily so `bajutsu.common.analytics.usage` stays free of the ledger's import at module load
    (the ledger imports `TokenUsage` from here), and so the deterministic core never pulls it in
    transitively.
    """
    with contextlib.suppress(Exception):
        from bajutsu.common.analytics import ledger

        ledger.emit(usage, provider=provider, model=model)


def snapshot() -> TokenUsage:
    """The cumulative usage so far. Take one before and after a feature, then subtract to get
    what that feature consumed (`usage.snapshot() - before`)."""
    return _TRACKER.snapshot()


def snapshot_by_category() -> dict[str, TokenUsage]:
    """The cumulative usage so far, split by call-site category (BE-0194 §4). Take one before and
    after a feature and subtract per category to get what each call site consumed."""
    return _TRACKER.snapshot_by_category()


def breakdown_lines(before: dict[str, TokenUsage], after: dict[str, TokenUsage]) -> list[str]:
    """Per-category delta lines to print under the one-line total (`before`/`after` from
    `snapshot_by_category`). A category with no spend between the snapshots is omitted, so a normal
    record shows only the buckets it actually used. Reporting only — never on the pass/fail path."""
    ordered = [*_CATEGORY_ORDER, *sorted(set(after) - set(_CATEGORY_ORDER))]
    lines = []
    for category in ordered:
        delta = after.get(category, TokenUsage()) - before.get(category, TokenUsage())
        if delta.calls:
            plural = "" if delta.calls == 1 else "s"
            lines.append(
                f"  {category}: {delta.total_tokens:,} tokens over {delta.calls} call{plural}"
            )
    return lines
