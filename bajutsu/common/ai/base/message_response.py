"""A model's reply, normalized so no caller reads a provider's own response shape."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .text_block import TextBlock
from .tool_use_block import ToolUseBlock

ContentBlock = TextBlock | ToolUseBlock


@dataclass(frozen=True)
class MessageResponse:
    """A normalized model response.

    ``usage`` is the provider's own token-accounting object, passed through untouched so
    `bajutsu.common.analytics.usage.record` reads it exactly as before (reporting only — never on the verdict path).
    """

    content: list[ContentBlock]
    stop_reason: str | None = None
    usage: Any = None

    def first_tool_use(self) -> ToolUseBlock | None:
        """The first tool-use block, or ``None`` when the model returned no tool call."""
        return next((b for b in self.content if isinstance(b, ToolUseBlock)), None)
