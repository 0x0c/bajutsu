"""One endpoint's declaration, shared by both server backends (BE-0253)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from bajutsu.serve.state import ServeState

from .request_ctx import RequestCtx

# A uniform route's adapter: extract this route's arguments from the request and call its `ops`
# function, returning the `(payload, status)` pair the backend writes as JSON (or text).
Handle = Callable[[ServeState, RequestCtx], tuple[Any, int]]


@dataclass(frozen=True)
class Route:
    """One endpoint's declaration, shared by both backends (BE-0253).

    Attributes:
        method: HTTP method — "GET", "POST", or "DELETE".
        path: FastAPI-style path template (e.g. "/api/orgs/{slug}/membership").
        handle: The uniform `(state, ctx) -> (payload, status)` adapter, or None for an
            `off_loop` route each backend handles bespoke.
        off_loop: The route writes its own response (streaming, file serve, raw upload, redirect)
            rather than the uniform JSON/text path; declared here but dispatched per backend.
        local_only: The FastAPI generator deliberately skips this route (Part 4's triage:
            `/api/ant/login`, `/api/capture/*`).
        content_type: When set, the response is text of this type instead of JSON.
    """

    method: str
    path: str
    handle: Handle | None = None
    off_loop: bool = False
    local_only: bool = False
    content_type: str | None = None
