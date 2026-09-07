"""A `for` wait's poll-by-poll record, filled in place so a timeout is diagnosable (BE-0231)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WaitTrace:
    """Poll-by-poll record of a `for` wait, filled in place so a timeout is diagnosable (BE-0231).

    On a first-wait timeout these fields separate the candidate causes: a tree that never became
    non-empty (`first_nonempty_s is None`) points at "nothing rendered / transient-empty"; a
    non-empty tree with `elements_at_timeout` content but a still-unmet target points at "the awaited
    element didn't render / readyWhen mismatch"; a large `first_nonempty_s` points at a slow
    cold-boot render. Pure diagnosis — it never enters a verdict (prime directive 1).
    """

    target: str = ""
    timeout_s: float = 0.0
    polls: int = 0
    first_nonempty_s: float | None = None
    elements_at_timeout: int = 0
