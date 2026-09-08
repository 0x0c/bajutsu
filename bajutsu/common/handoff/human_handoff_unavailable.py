"""The error raised when a `record` turn needs a human and no responder is available."""

from __future__ import annotations


class HumanHandoffUnavailable(RuntimeError):
    """Raised when a `record` turn needs a human but no responder is available.

    The non-interactive / CI case: the tooling stays deterministic by failing cleanly and
    labeled rather than hanging or letting the AI guess.
    """
