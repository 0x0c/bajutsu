"""The interactive handoff responder: ask the human on the terminal and read their answer."""

from __future__ import annotations

from bajutsu.common.handoff import DEFAULT_TIMEOUT_SECONDS, HandoffRequest, HandoffResponse

from ._functions import _read_line_bounded
from ._shared import Say


class PromptHandoff:
    """An interactive terminal responder: shows the request and reads the human's answer on stdin.

    The human types a value to supply it, `done` (or an empty line) after operating the device
    themselves, or `cancel` to stop the record. A silent responder times out to a cancel.
    """

    def __init__(self, say: Say, *, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        self._say = say
        self._timeout = timeout

    def request(self, request: HandoffRequest) -> HandoffResponse:
        self._say(f"✋ handoff needed: {request.reason}")
        if request.target:
            self._say(f"   target: {request.target}")
        if request.screen:
            self._say(f"   screen: {request.screen}")
        self._say(
            "   type a value to supply it, `done` after you operate the device, or `cancel` "
            f"(waiting up to {self._timeout:g}s) …"
        )
        line = _read_line_bounded(self._timeout)
        if line is None:
            self._say("   (no response — cancelling the handoff)")
            return HandoffResponse(cancelled=True)
        answer = line.strip()
        if answer.lower() == "cancel":
            return HandoffResponse(cancelled=True)
        if answer == "" or answer.lower() == "done":
            return HandoffResponse(acted=True)
        return HandoffResponse(values=[answer])
