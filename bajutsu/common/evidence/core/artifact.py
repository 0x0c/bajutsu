"""One captured file, tagged with how it was produced — the manifest's provenance record."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Artifact:
    """One captured file, tagged with how it was produced (manifest provenance)."""

    name: str
    kind: str
    provider: str
    # Which screen this file shows, as `"<driver>:<moment>"` — the driver whose read produced it,
    # and which side of the step's action it was taken on. Two artifacts describe the same screen
    # exactly when their `depicts` are equal, which is the entire contract: a consumer compares, and
    # never parses. `None` for a file that shows no screen (an interval recording, the wait
    # diagnostic) and for every run recorded before this field existed — where `step_view` falls
    # back to the pre-field choice rather than dropping frames a stored run has always shown.
    depicts: str | None = None
