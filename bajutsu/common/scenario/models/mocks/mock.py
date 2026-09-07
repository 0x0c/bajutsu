"""One deterministic network stub the app under test calls instead of the real service."""

from __future__ import annotations

from pydantic import Field

from bajutsu.common.scenario.models._base import _Model
from bajutsu.common.scenario.models.assertions import RequestMatch

from .mock_response import MockResponse


class Mock(_Model):
    """A deterministic network stub.

    When an outgoing request matches `match`, BajutsuKit returns `respond` instead of hitting the
    network (so tests don't depend on a live server). `match` reuses the request matcher's
    request-side fields (method / url / urlMatches / path / pathMatches / bodyMatches); status /
    count do not apply here.
    """

    match: RequestMatch
    respond: MockResponse = Field(default_factory=MockResponse)
