"""The tool choice that forces the model to call exactly one of the offered tools."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AnyTool:
    """Force the model to call exactly one of the offered tools (any of them)."""
