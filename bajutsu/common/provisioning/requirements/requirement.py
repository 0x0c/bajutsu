"""What a backend or capability needs: an optional pip extra plus its external tools."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .tool import Tool


@dataclass(frozen=True)
class Requirement:
    """What a backend or capability needs: an optional pip extra plus external tools."""

    extra: str | None = None
    tools: tuple[Tool, ...] = ()
