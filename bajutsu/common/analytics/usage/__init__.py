"""Token-usage accounting for the AI-backed paths.

Every Anthropic call in the tool — the authoring agent, the alert locator, the triage
agent — reports its response `usage` here, and the CLI commands read the running total to
show how many tokens a feature consumed. This is reporting only: it never touches the
deterministic pass/fail judgement, so recording is best-effort and must never raise.

The tracker is a process-global accumulator guarded by a lock: `run --workers N` shares one
alert locator across threads, so several threads can record concurrently. Commands take a
`snapshot()` before and after their work and show the difference — so a long-lived process
(e.g. the web server) reports per-invocation totals, not a process-lifetime sum.
"""

from ._accumulator import _Accumulator as _Accumulator
from ._functions import _CATEGORY_ORDER as _CATEGORY_ORDER
from ._functions import _TRACKER as _TRACKER
from ._functions import _emit_ledger_event as _emit_ledger_event
from ._functions import _field as _field
from ._functions import _int as _int
from ._functions import breakdown_lines, of, record, snapshot, snapshot_by_category
from ._shared import CATEGORY_ACTION, CATEGORY_ALERT, CATEGORY_OTHER, CATEGORY_PLAN
from .token_usage import TokenUsage

__all__ = [
    "CATEGORY_ACTION",
    "CATEGORY_ALERT",
    "CATEGORY_OTHER",
    "CATEGORY_PLAN",
    "TokenUsage",
    "breakdown_lines",
    "of",
    "record",
    "snapshot",
    "snapshot_by_category",
]
