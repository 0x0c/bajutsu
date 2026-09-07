"""Match a concrete path against a route template and bind its parameters."""

from __future__ import annotations

from collections.abc import Sequence

from .route import Route


def _match_template(template: str, path: str) -> dict[str, str] | None:
    """Match a concrete *path* against one FastAPI-style *template*, returning the bound path
    parameters (raw, not URL-decoded) or None. A `{name}` binds exactly one segment; a
    `{name:path}` (only valid as the final segment) binds the greedy remainder including slashes."""
    if "{" not in template:  # exact route — the common case
        return {} if template == path else None
    t_segs = template.split("/")
    p_segs = path.split("/")
    params: dict[str, str] = {}
    for i, seg in enumerate(t_segs):
        if seg.startswith("{") and seg.endswith("}"):
            name = seg[1:-1]
            if name.endswith(":path"):  # greedy remainder, must be the last template segment
                params[name[: -len(":path")]] = "/".join(p_segs[i:])
                return params
            if i >= len(p_segs):
                return None
            params[name] = p_segs[i]
        elif i >= len(p_segs) or p_segs[i] != seg:
            return None
    return params if len(p_segs) == len(t_segs) else None


def match_route(
    routes: Sequence[Route], method: str, path: str
) -> tuple[Route, dict[str, str]] | None:
    """The first route matching *method* and *path*, with its bound path parameters, or None.

    List order is precedence: a route listed before another that could also match a given path
    wins (e.g. `/runs/{run_id}/archive.zip` before the greedy `/runs/{rel:path}`)."""
    for route in routes:
        if route.method != method:
            continue
        params = _match_template(route.path, path)
        if params is not None:
            return route, params
    return None
