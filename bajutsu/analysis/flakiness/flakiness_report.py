from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .flaky_scenario import FlakyScenario


@dataclass(frozen=True)
class FlakinessReport:
    """The suite ranked by flakiness — flaky scenarios first, then by descending flip rate."""

    scenarios: list[FlakyScenario]  # flaky first, then flip_rate desc, then run count desc
    skipped: int  # runs dropped for lacking a fingerprint or a recorded verdict — ungroupable
