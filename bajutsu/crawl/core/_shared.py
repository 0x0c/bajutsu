"""The budgets, stop reasons, and identity rules a crawl explores under."""

from __future__ import annotations

from collections.abc import Callable

from .screen_map import ScreenMap

# Fires after each change to the map (a new node, edge, or crash). Pure observation so a caller
# can stream the screen map as it grows (the web UI's live graph) — it never influences which
# screen is explored next or how a screen is identified, so the crawl stays deterministic.
OnEvent = Callable[[ScreenMap], None]
