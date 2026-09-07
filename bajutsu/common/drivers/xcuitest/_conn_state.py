"""The per-lease state behind the channel's kept-alive connection (BE-0407)."""

from __future__ import annotations

import http.client
from dataclasses import dataclass


@dataclass
class _ConnState:
    """Mutable per-lease state for `_raw_http_transport`'s kept-alive connection (BE-0407 Unit 11).

    Plain fields rather than a bare `dict`, now that a second value — the monotonic time of the last
    successful call — travels alongside the connection itself to bound how long it may be reused
    before `_KEEPALIVE_IDLE_RECONNECT_SECONDS` forces a reconnect.
    """

    conn: http.client.HTTPConnection | None = None
    last_success_at: float | None = None
