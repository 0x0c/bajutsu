"""Which exchanges the network evidence keeps."""

from __future__ import annotations

from pydantic import Field

from bajutsu.common.scenario.models._base import _Model


class NetworkFilter(_Model):
    """Which observed requests to interleave into the report's Steps timeline.

    With `domains` set, only exchanges whose URL host matches one of them — exactly or as a
    parent suffix (`example.com` matches `api.example.com`) — appear in Steps; empty /
    unset shows every captured exchange. The Network tab always lists them all.
    """

    domains: list[str] = Field(default_factory=list)
