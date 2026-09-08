"""The lease timeouts and reclaim limits the repository enforces (BE-0016)."""

from __future__ import annotations

DEFAULT_LEASE_MAX_ATTEMPTS = 3

# The default newest-N window `list_runs` caps at (`None` means unbounded). Shared so the serve
# read path that re-caps a scoped list post-filter (`operations.reads`) stays in lock-step: a future
# bump here must not silently leave that path capping at a stale number.
DEFAULT_RUN_LIMIT = 50
