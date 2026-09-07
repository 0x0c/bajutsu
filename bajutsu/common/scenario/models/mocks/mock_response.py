"""The canned response a mock returns."""

from __future__ import annotations

from pydantic import Field

from bajutsu.common.scenario.models._base import _Model


class MockResponse(_Model):
    """The canned response a mock returns (defaults to an empty 200)."""

    status: int = 200
    headers: dict[str, str] = Field(default_factory=dict)
    body: str | None = None
    delay_ms: float | None = Field(default=None, alias="delayMs")  # artificial latency
