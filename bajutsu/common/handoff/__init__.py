"""Human-in-the-loop handoff contract (Tier 1, BE-0179).

The `record` loop can pause and hand control to a human — to supply a value the AI cannot
know (a one-time password), or to perform an operation the AI cannot (a CAPTCHA, a biometric
prompt) — then resume by re-observing the live screen. This module defines the
transport-neutral request/response contract so the terminal (`record` reading stdin) and the
Web UI (`serve` streaming the request over server-sent events and taking the response back
over the spawned-`record` process boundary) implement the same protocol.

The substrate owns the *mechanism* and the *boundary*: every handoff must resolve to a
re-runnable artifact, so a recording made with human help still replays with no human on the
deterministic `run` path. It deliberately does not pick the artifact shape (a value
placeholder versus an explicit manual step) — that is the child items' decision. What it
guarantees is that the human stays at authoring time and never lands on the `run` / CI gate.
"""

from ._functions import request_from_json, request_to_json, response_from_json, response_to_json
from ._shared import DEFAULT_TIMEOUT_SECONDS, REQUEST_LINE_PREFIX
from .handoff import Handoff
from .handoff_request import HandoffRequest
from .handoff_response import HandoffResponse
from .human_handoff_unavailable import HumanHandoffUnavailable

__all__ = [
    "DEFAULT_TIMEOUT_SECONDS",
    "REQUEST_LINE_PREFIX",
    "Handoff",
    "HandoffRequest",
    "HandoffResponse",
    "HumanHandoffUnavailable",
    "request_from_json",
    "request_to_json",
    "response_from_json",
    "response_to_json",
]
