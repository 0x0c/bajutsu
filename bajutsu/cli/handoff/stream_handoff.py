"""The `serve`-driven handoff responder: emit the request on stdout, read the answer on stdin."""

from __future__ import annotations

import sys

from bajutsu.common.handoff import (
    DEFAULT_TIMEOUT_SECONDS,
    REQUEST_LINE_PREFIX,
    HandoffRequest,
    HandoffResponse,
    request_to_json,
    response_from_json,
)

from ._functions import _read_line_bounded


class StreamHandoff:
    """A `serve`-driven responder: emits the request on stdout and reads the response from stdin.

    The request travels out as a `REQUEST_LINE_PREFIX`-tagged JSON line (`serve` turns it into a
    `human-request` event); the response arrives as a JSON line `serve` writes to this process's
    stdin. Bounded by *timeout* so a `serve` worker never hangs on an absent human.
    """

    def __init__(self, *, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        self._timeout = timeout

    def request(self, request: HandoffRequest) -> HandoffResponse:
        # A single flushed line so `serve`'s line-buffered reader sees it whole and at once.
        sys.stdout.write(f"{REQUEST_LINE_PREFIX}{request_to_json(request)}\n")
        sys.stdout.flush()
        line = _read_line_bounded(self._timeout)
        if line is None:
            # Narrate the cancel on the stream (not silently), so the record log shows *why* it ended.
            self._say(f"✋ no handoff response within {self._timeout:g}s — cancelling")
            return HandoffResponse(cancelled=True)
        try:
            return response_from_json(line)
        except ValueError:
            # A malformed response is not a value to guess — but serve builds it, so this signals a
            # transport bug; surface it rather than letting it masquerade as a human cancel.
            self._say("✋ malformed handoff response — cancelling")
            return HandoffResponse(cancelled=True)

    def _say(self, message: str) -> None:
        """Emit a line on stdout — the record narration stream `serve` relays to the browser."""
        sys.stdout.write(message + "\n")
        sys.stdout.flush()
