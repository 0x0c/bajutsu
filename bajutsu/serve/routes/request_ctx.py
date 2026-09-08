"""The backend-neutral view of one request a route's adapter reads."""

from __future__ import annotations

from typing import Any, Protocol


class RequestCtx(Protocol):
    """Backend-neutral view of one request, read by a route's `handle` adapter.

    The stdlib `Handler` and a FastAPI shim both satisfy this, so one adapter closure serves both
    backends.
    """

    def path_param(self, name: str) -> str:
        """The URL-decoded value bound to a `{name}` segment of the matched path template.

        Both backends return the decoded segment: the stdlib ctx `unquote`s the raw match, the
        FastAPI ctx passes Starlette's already-decoded param. A closure therefore never decodes,
        so the two backends can't drift on how a percent-encoded segment reaches its `ops` call.
        """
        ...

    def query(self, key: str) -> str | None:
        """The first value of query parameter *key*, or None."""
        ...

    def body(self) -> dict[str, Any]:
        """The parsed JSON request body (an empty dict for a GET)."""
        ...

    def actor(self) -> str | None:
        """The GitHub login bound to this request's session, or None."""
        ...

    def session(self) -> str | None:
        """This request's opaque login-session id, or None for a shared-token / anonymous caller.

        The scope a member's own configuration binding lives in (BE-0393 unit 2): an operation that
        reads the bound configuration resolves it through `state.binding_for(session, org)`, so a
        bind made in one session is invisible to every other.
        """
        ...
