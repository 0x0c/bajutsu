"""The `select` action: select a field's content before a consuming action (BE-0265)."""

from __future__ import annotations

from typing import Literal

from bajutsu.common.scenario.models._base import _Model
from bajutsu.common.scenario.models.selector import Selector


class SelectText(_Model):
    """`select` action — select a field's content before a consuming action (copy / type-over).

    `mode: all` (the only mode for now) selects the whole current content via the platform's
    select-all. Kept an action, not queryable state: no backend exposes a selection range through
    its element surface, so its outcome is only ever verified through what follows it — a `copy`
    (clipboard read-back) or a `type` that replaces the selection (`value` assertion) — never
    asserted directly (BE-0265).
    """

    into: Selector
    mode: Literal["all"] = "all"
