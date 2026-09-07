"""Everything triage needs to reason about one failed scenario."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from bajutsu.common.drivers import base

if TYPE_CHECKING:
    from .failed_step import FailedStep


@dataclass(frozen=True)
class TriageContext:
    """Everything needed to reason about one failed scenario."""

    scenario: str
    failure: str
    failed_step: FailedStep | None
    failed_expectations: list[str]
    elements: list[base.Element]  # the a11y tree nearest the failure
    scenario_yaml: str  # the failing scenario's definition
    target_id: str | None  # the failing step's selector id, if any
    evidence: list[str] = field(default_factory=list)
    screenshot: bytes | None = None  # the screenshot nearest the failure, if one was captured
