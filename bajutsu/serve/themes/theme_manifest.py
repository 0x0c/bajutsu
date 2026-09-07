"""What the picker needs to list a theme: its id, display name, and kind."""

from __future__ import annotations

from dataclasses import dataclass

from ._shared import ThemeKind


@dataclass(frozen=True)
class ThemeManifest:
    """What the picker needs to list a theme: its `[data-theme]` id, display name, and kind."""

    id: str
    name: str
    kind: ThemeKind
