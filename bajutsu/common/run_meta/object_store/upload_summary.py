"""How an upload walk ended: how many files went up, and which failed."""

from __future__ import annotations

import dataclasses


@dataclasses.dataclass(frozen=True)
class UploadSummary:
    """The outcome of an `upload_tree` walk: how many files went up, and any that failed.

    *failures* pairs each failed key with a short reason; it is empty on a clean upload. The upload
    never raises for a per-file error (BE-0110: an upload failure must not change the run verdict) —
    the caller inspects this to report."""

    uploaded: int
    failures: list[tuple[str, str]]
