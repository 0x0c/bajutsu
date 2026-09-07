"""Bajutsu's own verdict for a Device Farm run, read back from the downloaded manifests."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Verdict:
    """Bajutsu's verdict for a Device Farm run, read from the downloaded ``manifest.json`` tree."""

    ok: bool
    passed: int
    total: int
    failures: list[str] = field(default_factory=list)
