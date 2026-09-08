"""The target's resolved evidence directory overrides (BE-0252)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvidenceDirs:
    """The target's evidence directory overrides (BE-0252 grouping of `Effective`).

    Each is the target's directory for that evidence kind (config-driven `run`/`record`). None
    means "unset": scenarios then requires an explicit path, and each of baselines / schemas /
    goldens falls back to the directory beside the scenario file (or the matching `--<kind>` flag).
    """

    scenarios: str | None = None
    baselines: str | None = None
    schemas: str | None = None
    goldens: str | None = None
