"""How the Device Farm host reaches the reserved device for one platform."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class _PlatformRun:
    """How the Device Farm host reaches the reserved device for one platform.

    `backend` is Bajutsu's ``--backend``; `udid` is the shell-ready ``--udid`` argument spliced into
    the run command (a fixed alias, or an environment reference the host expands); `probe` runs in
    `pre_test` to prove the reserved device is visible before the run.
    """

    backend: str
    udid: str
    probe: str
