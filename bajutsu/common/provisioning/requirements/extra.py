"""The install method for a tool a pip extra provides."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Extra:
    """Provided by syncing a pip extra (``uv sync --extra <name>``)."""

    name: str
