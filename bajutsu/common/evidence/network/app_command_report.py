"""The app's report on one command it drained (BE-0365)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class AppCommandReport(BaseModel):
    """The app's report on one command it drained (BE-0365).

    Inbound, so forward-compatible like the exchange and transition reports — but `applied` carries
    no default, because "applied it" and "drained it and could not apply it" must not reach the
    acknowledgement wait as the same message, and a default would quietly make one of them the
    other. An app whose capability was compiled out, or whose handler raised, says so here with its
    own `reason`, so the wait fails with the cause rather than timing out blind (BE-0365 unit 3).
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore", frozen=True)

    id: str
    applied: bool
    reason: str = ""
