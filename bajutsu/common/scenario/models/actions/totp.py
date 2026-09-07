"""The `totp` action: generate an RFC 6238 one-time password into a variable (BE-0046)."""

from __future__ import annotations

from bajutsu.common.scenario.models._base import _Model

from .var_target import VarTarget


class Totp(_Model):
    """`totp` — generate an RFC 6238 time-based one-time password into `${vars.*}` (BE-0046).

    `secret` is the shared base32 key (commonly `${secrets.*}`); the current code is written to
    `into.var` for a later `type` / `assert` to consume. Local and deterministic — no LLM, no
    network, no scripting escape hatch.
    """

    secret: str
    into: VarTarget
