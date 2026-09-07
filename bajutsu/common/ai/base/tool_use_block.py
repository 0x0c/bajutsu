"""A tool-use request in a normalized model response: the tool name and its arguments."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolUseBlock:
    """A tool-use request in a model response: the tool name and its argument object."""

    name: str
    input: dict[str, Any]
