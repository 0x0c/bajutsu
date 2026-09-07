"""The paths a `golden` assertion reads and writes (BE-0006)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bajutsu.common.drivers import base


@dataclass(frozen=True)
class GoldenContext:
    """Paths a `golden` assertion needs (BE-0006).

    The golden JSON path (from the assertion's `path` field) is resolved against `goldens_dir`.
    `screen`, when given, is the authoritative device screen bounds for frame sanity checks;
    when absent, the bounds are derived from the live elements — a weaker fallback since
    elements at the screen edge make the check tautological for overflow detection.
    """

    goldens_dir: Path
    screen: base.Frame | None = None
