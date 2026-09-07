"""The network condition a `for` wait can block on."""

from __future__ import annotations

from bajutsu.common.scenario.models._base import _Model

from .request_match import RequestMatch


class WaitRequest(_Model):
    """`until: { request: <RequestMatch> }` — wait until a matching network exchange has been observed.

    Requires the run's network collector to be active.
    """

    request: RequestMatch
