"""The resolved doctor id-coverage thresholds, grouped out of `Effective` (BE-0024, BE-0252)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DoctorThresholds:
    """Configurable doctor id-coverage thresholds (BE-0024), grouped out of `Effective` (BE-0252).

    Teams with many decorative elements can tune thresholds (often lowering ok and/or fail for
    leniency) without changing the tool.
    """

    ok_coverage: float = 0.9
    fail_coverage: float = 0.7
