"""Which of Bajutsu's three answer paths a system prompt can be answered on."""

from __future__ import annotations

from typing import TypedDict


class AlertSurfaces(TypedDict):
    """Which of Bajutsu's three answer paths a prompt can actually be declared and answered on.

    Recorded per prompt because `savePassword` is the first to diverge (BE-0406): iOS raises it into
    the application's own process, so `springboard.alerts` never sees it and only the guard's in-tree
    dismissal can clear it. Three consumers read this — the `handleSystemAlert` step rejects a prompt
    it could never resolve, the in-tree paths arm only on rules a tree match can reach, and the
    interruption policy pushed to the runner drops a rule that surface can never meet.
    """

    step: bool
    native: bool
    in_tree: bool
