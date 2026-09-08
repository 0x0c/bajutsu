"""A job a worker has leased — the boundary type the seam hands out."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class LeasedJob:
    """A job that has been leased by a worker — the boundary type the seam hands out."""

    id: str
    org_id: str
    spec: dict[str, Any]
