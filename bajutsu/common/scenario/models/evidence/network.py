"""The network evidence a scenario asks its run to record."""

from __future__ import annotations

from bajutsu.common.scenario.models._base import _Model

from .network_filter import NetworkFilter


class Network(_Model):
    """Per-scenario network settings.

    `filter` scopes which observed requests are interleaved into the report's Steps timeline.
    """

    filter: NetworkFilter | None = None
