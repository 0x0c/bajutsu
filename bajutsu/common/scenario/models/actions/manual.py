"""The `manual` action: the human-takeover marker `record` writes (BE-0185)."""

from __future__ import annotations

from pydantic import Field

from bajutsu.common.scenario.models._base import _Model


class Manual(_Model):
    """`manual` action — a human-takeover marker recorded during `record` (BE-0185).

    Emitted when a blocker is an *operation* the AI cannot perform (a CAPTCHA, a biometric prompt,
    a repeatedly unresolvable gesture): the human operated the device live and `record` recorded
    this marker of the observed transition, not the raw gesture. It has no deterministic run-time
    equivalent, so at `run` time it fails loudly with `label` — never a silent pass, never a hang
    (directives 1 and 2). `bypass`, when set, names the deterministic bridge an author can wire to
    make the step replayable (a test-build flag, a device-control / device-state primitive,
    BE-0035 / BE-0052); None means no such bridge exists (a real CAPTCHA).
    """

    label: str = Field(min_length=1)
    bypass: str | None = None
