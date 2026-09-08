"""What the enrichment agent sees for one replayed step: the step and the screen after it."""

from __future__ import annotations

from dataclasses import dataclass

from bajutsu.common.drivers import base
from bajutsu.common.scenario import Step

# ---------------------------------------------------------------------------
# Enrichment (BE-0014)
# ---------------------------------------------------------------------------


@dataclass
class StepContext:
    """What the enrichment agent sees for one replayed step: the step and the screen after it."""

    step: Step
    screen: list[base.Element]
    screenshot: bytes | None = None
