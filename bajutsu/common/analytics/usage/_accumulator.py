"""The thread-safe per-category running total behind the process-wide usage tracker (BE-0194)."""

from __future__ import annotations

from threading import Lock
from typing import Any

from ._shared import CATEGORY_OTHER
from .token_usage import TokenUsage


class _Accumulator:
    """Thread-safe running total of token counts across AI responses, kept per category (BE-0194).

    The categories partition every recorded call (each lands in exactly one), so their sum is the
    running total — `snapshot()` folds them back together for callers that want just the total.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._by_category: dict[str, TokenUsage] = {}

    def record(self, usage: Any, category: str = CATEGORY_OTHER) -> None:
        """Add one response's `usage` to `category`'s running total. Best-effort: a `None` usage (a
        mocked client, or an SDK that omitted it) is ignored, and a missing field counts as
        zero — recording never raises and never affects pass/fail."""
        if usage is None:
            return
        # Imported in the method, not at module load: `_functions` builds its module-level tracker
        # from this class, and rule 5 breaks the cycle the split creates on this side because that
        # one cannot be deferred.
        from ._functions import of

        one = of(usage)
        with self._lock:
            self._by_category[category] = self._by_category.get(category, TokenUsage()) + one

    def snapshot(self) -> TokenUsage:
        with self._lock:
            return sum(self._by_category.values(), TokenUsage())

    def snapshot_by_category(self) -> dict[str, TokenUsage]:
        with self._lock:
            return dict(self._by_category)
