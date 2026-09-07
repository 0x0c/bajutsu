"""A drop-in theme: its manifest plus the CSS block inlined verbatim."""

from __future__ import annotations

from dataclasses import dataclass

from .theme_manifest import ThemeManifest


@dataclass(frozen=True)
class DiscoveredTheme:
    """A drop-in theme: its manifest plus the raw CSS block to inline verbatim."""

    manifest: ThemeManifest
    css: str
