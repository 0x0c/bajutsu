"""Pick the handoff responder a `record` invocation gets, and read stdin under a deadline."""

from __future__ import annotations

import select
import sys

from bajutsu.common.handoff import Handoff

from ._shared import Say


def _read_line_bounded(timeout: float) -> str | None:
    """Read one line from stdin, waiting at most *timeout* seconds; None on timeout or EOF."""
    try:
        ready, _, _ = select.select([sys.stdin], [], [], timeout)
    except (OSError, ValueError):
        return None  # stdin has no waitable fd (closed / not a real stream): treat as no responder
    if not ready:
        return None
    line = sys.stdin.readline()
    return line if line else None  # readline == "" means EOF (the write end closed)


def make_handoff(mode: str, *, say: Say) -> Handoff | None:
    """The handoff responder for a `record` invocation, or None when there is no responder.

    `auto` (the default) is interactive when stdin is a TTY, else None — so CI, with no human,
    gets the clean labeled failure. `prompt` / `stream` force the terminal / `serve` responder;
    `off` forces no responder. An unknown mode raises rather than silently degrading to `auto`,
    so a typo (`--handoff promt`) fails loudly instead of quietly changing whether `record` can pause.
    """
    # Imported in the body, not at module load: both responders call `_read_line_bounded` above,
    # so rule 5 breaks the cycle the split creates on the factory's single edge rather than on
    # each responder's.
    from .prompt_handoff import PromptHandoff
    from .stream_handoff import StreamHandoff

    if mode == "off":
        return None
    if mode == "prompt":
        return PromptHandoff(say)
    if mode == "stream":
        return StreamHandoff()
    if mode == "auto":
        return PromptHandoff(say) if sys.stdin.isatty() else None
    raise ValueError(f"unknown handoff mode: {mode!r} (expected auto | prompt | stream | off)")
