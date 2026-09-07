"""One screen transition the app's own observer reported (BE-0310)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ScreenTransition(BaseModel):
    """One screen-transition event the app's `BajutsuScreen` observer reported (BE-0310).

    Minimal by design: no screen content, only what a positive "the transition finished"
    signal needs. Extra keys are ignored and the app's own `timestamp` is informational only —
    the collector stamps its own receive time (`snapshot_timed`), the same monotonic clock
    domain the readiness gate and the `settled` wait already poll in, so nothing here depends on
    the app process's separate clock.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    kind: str = ""
