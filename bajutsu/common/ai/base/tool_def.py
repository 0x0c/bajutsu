"""A tool offered to the model: its name, description, and JSON-schema input shape."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolDef:
    """A tool the model may call: its name, description, and JSON-schema input shape."""

    name: str
    description: str
    input_schema: dict[str, Any]
