"""The bounded, cancelable channel that asks a human and returns their response."""

from __future__ import annotations

from typing import Protocol

from .handoff_request import HandoffRequest
from .handoff_response import HandoffResponse


class Handoff(Protocol):
    """A bounded, cancelable channel that asks a human and returns their response.

    Implementations block on a human but never unbounded: a responder who never answers
    resolves to a cancelled response, never a hang. `record` calls this when a turn's outcome
    is "needs human".
    """

    def request(self, request: HandoffRequest) -> HandoffResponse:
        """Present *request* to the human and return their response (cancelled on timeout)."""
