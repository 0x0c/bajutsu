"""One normalized turn to send to a backend, whichever provider serves it."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .any_tool import AnyTool
from .named_tool import NamedTool

if TYPE_CHECKING:
    from .message import Message
    from .tool_def import ToolDef


# Every current path forces a tool call — either "call some tool" or "call this tool". Free-choice
# (optional tool use) is not modeled because no path uses it.
ToolChoice = AnyTool | NamedTool


@dataclass(frozen=True)
class MessageRequest:
    """A single normalized turn to send to a backend.

    ``system`` is a plain string; the adapter applies whatever prompt-caching the provider offers
    (all paths cache the static system prompt today). ``tool_choice`` forces a tool call, so a
    compliant response carries a tool-use block — callers still check
    ``MessageResponse.first_tool_use()`` for the rare case a model doesn't comply.
    """

    system: str
    messages: list[Message]
    tools: list[ToolDef]
    tool_choice: ToolChoice
    model: str
    max_tokens: int
    # Reasoning-effort level (low/medium/high/xhigh/max) for backends that support it — the
    # `claude-code` CLI does (`--effort`); the SDK adapters have no such knob and ignore it.
    effort: str | None = None
    # Wall-clock cap (seconds) for this one call, or None for the backend default. A best-effort call
    # (e.g. the up-front plan) sets a short cap so a hung CLI fails fast instead of blocking the run.
    timeout_s: float | None = None
