"""Self-contained HTML screen map for a crawl (BE-0038).

The visual, offline counterpart to the web UI's live graph: a pure, deterministic function of a
`ScreenMap` (the crawl's already-captured model) into a single HTML page — screens laid out in BFS
depth columns, transitions drawn as a static inline SVG, each screen linked to its screenshot. No
device, no model, no JavaScript, no external asset, so it opens straight from the run dir. It only
visualizes what the crawl already found; it never influences the (deterministic) exploration.
"""

from ._functions import _COLW as _COLW
from ._functions import _NH as _NH
from ._functions import _NW as _NW
from ._functions import _PAD as _PAD
from ._functions import _ROWH as _ROWH
from ._functions import _TEMPLATE_DIR as _TEMPLATE_DIR
from ._functions import _edges as _edges
from ._functions import _env as _env
from ._functions import layout, render_html, write_html
from .box import Box
from .edge_line import EdgeLine
from .layout import Layout

__all__ = ["Box", "EdgeLine", "Layout", "layout", "render_html", "write_html"]
