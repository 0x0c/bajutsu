"""Drop-in theme discovery for the serve Web UI (BE-0191 unit 2).

A theme is declarative only — a CSS block of the tokens documented in
``bajutsu/templates/serve.themes.css`` plus a small manifest (display name and a ``dark`` /
``light`` kind). It carries no JavaScript, so a dropped-in theme sits at the same trust level as
the operator's scenarios and config while limiting the surface to CSS. Serve scans the ``--themes``
directory once at startup; the discovered CSS is folded into the inlined theme stylesheet and the
manifest is handed to the client so the picker (unit 3) can list the options. ``ui.default_theme``
is the serve-only initial selection, read here rather than modeled in the core ``Config`` — the
same split the ``orgs:`` block uses (BE-0129).
"""

from ._functions import _KIND as _KIND
from ._functions import _MANIFEST_COMMENT as _MANIFEST_COMMENT
from ._functions import _NAME as _NAME
from ._functions import (
    BUILTIN_THEMES,
    discover_themes,
    parse_theme_tokens,
    read_default_theme,
    theme_manifests,
)
from ._functions import _log as _log
from ._functions import _parse_manifest as _parse_manifest
from ._shared import ThemeKind
from .discovered_theme import DiscoveredTheme
from .theme_manifest import ThemeManifest

__all__ = [
    "BUILTIN_THEMES",
    "DiscoveredTheme",
    "ThemeKind",
    "ThemeManifest",
    "discover_themes",
    "parse_theme_tokens",
    "read_default_theme",
    "theme_manifests",
]
