"""The error raised for a recorded `manual` step with no deterministic equivalent (BE-0185)."""

from __future__ import annotations

from .unsupported_action import UnsupportedAction


class ManualStepRequired(UnsupportedAction):
    """A recorded `manual` takeover step has no deterministic run-time equivalent (BE-0185).

    Raised at `run` time so a human-takeover marker (a CAPTCHA, a biometric prompt) fails loudly and
    visibly with its label rather than a silent pass or a hang — the honest boundary for an operation
    only a human can perform. A subclass of `UnsupportedAction` so the run loop surfaces it as a
    clean, labeled step failure like any other action the environment cannot perform.
    """
