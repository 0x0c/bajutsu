"""The format-neutral run summary every notification channel renders from."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .failure_summary import FailureSummary


@dataclass
class RunNotification:
    """The format-neutral summary projected from run results."""

    run_id: str
    ok: bool
    total: int
    passed: int
    failed: int
    source_name: str
    backend: str
    duration_s: float
    failures: list[FailureSummary]
    failures_remaining: int
    report_url: str | None
    engine: str
