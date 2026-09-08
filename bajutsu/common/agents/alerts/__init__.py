"""System-alert guard — detect and dismiss OS prompts the app cannot see.

The iOS accessibility query is scoped to the foreground app, so SpringBoard-level
prompts (e.g. the iOS "Save Password?" alert) are invisible to it and silently
block a run: the app's element tree collapses to a single window node. This guard
takes a screenshot, asks a vision locator where to tap, and taps it by coordinate.
The locator dismisses the prompt by default, or follows a specific instruction
when one is configured for it.

The locator is injectable: production uses Claude vision; tests and offline runs
inject a deterministic one. Coordinates are image-normalized [0,1] so they map to
the device's point-space screen regardless of the screenshot's pixel scale.
"""

from ._functions import _decision_of as _decision_of
from .alert_decision import AlertDecision
from .alert_locator import AlertLocator
from .claude_alert_locator import LOCATOR_MODEL, LOCATOR_SYSTEM, LOCATOR_TOOL, ClaudeAlertLocator
from .system_alert_guard import SystemAlertGuard
from .system_alert_guard import _logger as _logger

__all__ = [
    "LOCATOR_MODEL",
    "LOCATOR_SYSTEM",
    "LOCATOR_TOOL",
    "AlertDecision",
    "AlertLocator",
    "ClaudeAlertLocator",
    "SystemAlertGuard",
]
