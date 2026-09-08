"""Handoff responders for `record` (BE-0179).

Two implementations of the `Handoff` contract, both bounded and cancelable:

- `PromptHandoff` — a terminal author answers at an interactive stdin prompt.
- `StreamHandoff` — `serve` drives the record: the request is emitted as a sentinel line on
  stdout (which `serve` lifts into a `human-request` server-sent event) and the response is read
  back from stdin (which `serve` feeds over the spawned-`record` process boundary).

Both read stdin through a bounded `select`, so a responder who never answers resolves to a
cancelled response rather than an unbounded hang. When no responder is available at all
(non-interactive, no `serve`), `record` gets no handoff and fails cleanly instead (the CLI maps
that to a labeled non-zero exit) — the human never lands on the deterministic `run` path.
"""

from ._functions import _read_line_bounded as _read_line_bounded
from ._functions import make_handoff
from ._shared import Say
from .prompt_handoff import PromptHandoff
from .stream_handoff import StreamHandoff

__all__ = ["PromptHandoff", "Say", "StreamHandoff", "make_handoff"]
