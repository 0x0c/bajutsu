"""One drain's interruption-time answers, as orchestrator-level records."""

from __future__ import annotations

from dataclasses import dataclass

from .alert_event import AlertEvent
from .undeclared_interruption import UndeclaredInterruption


@dataclass(frozen=True)
class DrainedInterruptionEvents:
    """One drain's worth of interruption-time answers, translated to orchestrator-level records."""

    alerts: list[AlertEvent]
    undeclared: list[UndeclaredInterruption]
