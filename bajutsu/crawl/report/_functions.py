"""Lay a screen map out deterministically and render it as one self-contained page."""

from __future__ import annotations

import functools
from collections import deque
from pathlib import Path, PurePosixPath

from jinja2 import Environment, FileSystemLoader

from bajutsu.common.evidence.sink import RunArtifactWriter
from bajutsu.common.run_meta.files import RunArtifactReader
from bajutsu.crawl.core import ScreenMap

from .box import Box
from .edge_line import EdgeLine
from .layout import Layout

# Box + grid geometry. The *layout algorithm* is ported from the web UI's layered graph
# (templates/serve.js); these constants are retuned for the static card (a smaller thumbnail, no
# expand button), so they intentionally differ from the live UI's. A card is NW by NH, columns are
# COLW apart (depth), rows ROWH apart (siblings), with a PAD margin.
_NW, _NH, _COLW, _ROWH, _PAD = 176, 200, 240, 230, 24


# The shared Jinja templates live at the package root (`bajutsu/templates/`), one level up now
# that this module is inside the `crawl/` package (BE-0257).
_TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "templates"


def layout(screen_map: ScreenMap, have_screens: frozenset[str] = frozenset()) -> Layout:
    """Place the screens on a BFS-depth grid and route the transitions. Pure and deterministic.

    Depth is the BFS distance over non-self transitions from a root (a screen nothing leads into,
    falling back to the first); screens at the same depth share a column, stacked in fingerprint
    order. Mirrors the web UI's layered layout so the static map reads the same as the live one.
    """
    fps = sorted(screen_map.nodes)  # fingerprint order -> deterministic within-layer placement
    adj: dict[str, list[str]] = {fp: [] for fp in fps}
    incoming: set[str] = set()
    for e in screen_map.edges:
        if e.src != e.dst and e.src in adj and e.dst in adj:
            adj[e.src].append(e.dst)
            incoming.add(e.dst)

    roots = [fp for fp in fps if fp not in incoming] or fps[:1]
    depth: dict[str, int] = dict.fromkeys(roots, 0)
    queue = deque(roots)
    while queue:
        f = queue.popleft()
        for t in adj[f]:
            if t not in depth:
                depth[t] = depth[f] + 1
                queue.append(t)
    for fp in fps:  # a screen unreachable over non-self edges still gets a column-0 slot
        depth.setdefault(fp, 0)

    layers: dict[int, list[str]] = {}
    for fp in fps:
        layers.setdefault(depth[fp], []).append(fp)

    pos: dict[str, tuple[int, int]] = {}
    max_rows = 1
    for d, layer in layers.items():
        max_rows = max(max_rows, len(layer))
        for i, fp in enumerate(layer):
            pos[fp] = (_PAD + d * _COLW, _PAD + i * _ROWH)

    boxes = [
        Box(
            fp=fp,
            kind=screen_map.nodes[fp].kind,
            ids=screen_map.nodes[fp].ids,
            actions=screen_map.nodes[fp].actions,
            x=pos[fp][0],
            y=pos[fp][1],
            has_shot=fp in have_screens,
        )
        for fp in fps
    ]
    n_layers = max(layers) + 1 if layers else 1
    width = _PAD * 2 + (n_layers - 1) * _COLW + _NW
    height = _PAD * 2 + (max_rows - 1) * _ROWH + _NH
    return Layout(boxes=boxes, edges=_edges(screen_map, pos), width=width, height=height)


def _edges(screen_map: ScreenMap, pos: dict[str, tuple[int, int]]) -> list[EdgeLine]:
    """Route one SVG path per source→target pair (parallel transitions collapse to one line)."""
    # Aggregate to one line per pair, amber if any underlying transition tapped through an alert —
    # the action detail lives on the screen cards, so the graph stays one arrow per pair.
    agg: dict[tuple[str, str], bool] = {}
    for e in screen_map.edges:
        if e.src in pos and e.dst in pos:
            agg[(e.src, e.dst)] = agg.get((e.src, e.dst), False) or bool(e.alert)

    lines: list[EdgeLine] = []
    for (src, dst), alert in agg.items():
        ax, ay = pos[src]
        bx, by = pos[dst]
        if src == dst:  # self-loop: a small lobe off the card's right edge
            x, y = ax + _NW, ay + _NH // 2
            d = f"M{x},{y - 8} C{x + 34},{y - 26} {x + 34},{y + 26} {x},{y + 8}"
            lines.append(EdgeLine(d=d, alert=alert, mark_x=x + 30, mark_y=y))
        else:
            x1, y1 = ax + _NW, ay + _NH // 2
            x2, y2 = bx, by + _NH // 2
            mx = (x1 + x2) // 2
            d = f"M{x1},{y1} C{mx},{y1} {mx},{y2} {x2},{y2}"
            lines.append(EdgeLine(d=d, alert=alert, mark_x=mx, mark_y=(y1 + y2) // 2 - 4))
    return lines


@functools.lru_cache(maxsize=1)
def _env() -> Environment:
    # autoescape so a stray "<" in an id can never inject markup into the page.
    return Environment(loader=FileSystemLoader(str(_TEMPLATE_DIR)), autoescape=True)


def render_html(
    screen_map: ScreenMap, run_id: str = "", have_screens: frozenset[str] = frozenset()
) -> str:
    """A self-contained HTML screen map (inline CSS, no JavaScript, no external asset).

    `have_screens` is the set of fingerprints with a captured screenshot — only those cards link a
    thumbnail (so a missing capture never shows a broken image). Read-only and model-free.
    """
    lay = layout(screen_map, have_screens)
    return (
        _env()
        .get_template("crawl.html.j2")
        .render(
            run_id=run_id,
            lay=lay,
            screens=len(screen_map.nodes),
            transitions=len(screen_map.edges),
            crashes=screen_map.crashes,
            alerts=screen_map.alerts,
            stop_reason=screen_map.stop_reason,
            short=lambda fp: fp[:7],
        )
    )


def write_html(
    writer: RunArtifactWriter, reader: RunArtifactReader, screen_map: ScreenMap, run_id: str = ""
) -> str:
    """Write `screenmap.html` into the run dir, beside `screenmap.json` and `screens/`.

    Lists `screens/*.png` so each captured screen links its thumbnail by a relative path that
    resolves when the report is opened straight from the run dir. Returns the artifact name.

    The report is a self-contained file meant to be shared, which is why it goes through the sink
    rather than writing itself. Only the sink's free-text pass reaches it, though: the structural
    screen-map masking runs over `screenmap.json` alone, so this page must never render an action's
    `value` or `fields` (BE-0331).
    """
    have = frozenset(PurePosixPath(n).stem for n in reader.names("screens/*.png"))
    name = "screenmap.html"
    writer.write_text(name, render_html(screen_map, run_id or reader.run_id, have))
    return name
