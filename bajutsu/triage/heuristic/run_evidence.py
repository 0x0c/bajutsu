"""One run's evidence for cross-run flaky triage: its verdict and the state nearest its end."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bajutsu.common.drivers import base

if TYPE_CHECKING:
    from .failed_step import FailedStep


@dataclass(frozen=True)
class RunEvidence:
    """One run's evidence for cross-run flaky triage — its verdict and the state nearest its end.

    For a failing run the state is captured nearest the failed step; for a passing run there is no
    failure, so it is the element tree / screenshot captured at the run's end.
    """

    run_id: str
    ok: bool
    failure: str
    failed_step: FailedStep | None
    failed_expectations: list[str]
    elements: list[base.Element]  # a11y tree nearest the failure (failing) or run end (passing)
    screenshot: bytes | None = None
