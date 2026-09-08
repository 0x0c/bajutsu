"""The tool choice that forces the model to call the one named tool."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NamedTool:
    """Force the model to call the one named tool."""

    name: str
