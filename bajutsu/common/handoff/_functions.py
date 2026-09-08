"""Serialize a handoff request and read its response back off the stream."""

from __future__ import annotations

import base64
import json

from .handoff_request import HandoffRequest
from .handoff_response import HandoffResponse


def request_to_json(request: HandoffRequest) -> str:
    """Serialize a handoff request for the stdout stream / server-sent event (screenshot base64)."""
    shot = base64.b64encode(request.screenshot).decode("ascii") if request.screenshot else None
    return json.dumps(
        {
            "reason": request.reason,
            "screen": request.screen,
            "target": request.target,
            "screenshot": shot,
        }
    )


def request_from_json(payload: str) -> HandoffRequest:
    """Parse a handoff request from its serialized form.

    Raises `ValueError` on anything that is not a JSON object (like `response_from_json`), so a
    malformed line on the cross-process channel fails clearly rather than crashing with an
    `AttributeError` on `.get`.
    """
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("handoff request must be a JSON object")  # noqa: TRY004  # invalid external payload, not a caller type error
    shot = data.get("screenshot")
    return HandoffRequest(
        reason=str(data.get("reason", "")),
        screen=str(data.get("screen", "")),
        target=str(data.get("target", "")),
        screenshot=base64.b64decode(shot) if shot else None,
    )


def response_to_json(response: HandoffResponse) -> str:
    """Serialize a handoff response for the response channel (stdin / the response endpoint)."""
    return json.dumps(
        {"values": response.values, "acted": response.acted, "cancelled": response.cancelled}
    )


def response_from_json(payload: str) -> HandoffResponse:
    """Parse a handoff response from its serialized form.

    Raises `ValueError` on anything that is not a JSON object — malformed text, or valid JSON that
    is a list / string / number / null. The `StreamHandoff` responder maps that to a cancel, so a
    bad response never crashes `record` with an `AttributeError`.
    """
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("handoff response must be a JSON object")  # noqa: TRY004  # invalid external payload, not a caller type error
    return HandoffResponse.from_dict(data)
