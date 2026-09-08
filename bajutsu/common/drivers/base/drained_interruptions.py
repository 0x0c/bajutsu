"""One drain's record from the interruption monitor: what it tapped, and what it declined."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DrainedInterruptions:
    """One drain's worth of what the interruption monitor did: what it tapped, and what it declined.

    `declined` is the button lists of alerts the policy governed but no rule identified — a monitor
    that declines still has to answer XCUITest's alert (its own default button, unchanged), so this
    is not a second dismissal outcome, only a record of what the tap was never asked to be. Reported
    so the caller can fail the step/expect that met one, naming what was on screen, rather than
    letting the run continue as if nothing had answered on the scenario's behalf (BE-0406 Unit 2b).
    """

    tapped: list[str]
    declined: list[list[str]]
