"""The seam for spotting a blocking system prompt in a screenshot and deciding where to tap."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from .alert_decision import AlertDecision


class AlertLocator(Protocol):
    """Given a screenshot, decide whether a blocking prompt is up and where to tap."""

    def locate(self, screenshot_png: bytes, instruction: str | None) -> AlertDecision: ...
