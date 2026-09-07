"""A system prompt the guard dismissed so a blocked step could proceed."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AlertEvent:
    """A system prompt the guard dismissed so a blocked step/expect could proceed.

    Recorded on the outcome (StepOutcome.alerts / RunResult.expect_alerts) and surfaced in
    the report, so a step that only passed on a retry isn't shown as if nothing had blocked
    it. `label` is the button the guard tapped (e.g. "Not Now"); empty when the locator
    named none."""

    label: str = ""
