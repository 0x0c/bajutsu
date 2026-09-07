"""What starting a browser hands back to the driver."""

from __future__ import annotations

from typing import Any, NamedTuple

from ._page import _Page


class _Started(NamedTuple):
    """What a `Starter` returns.

    `browser` / `pw` are held to tear down in close(); `context` is held
    so a per-visit reset can close it before opening a fresh one (BE-0077), bounding live contexts to
    one per worker rather than leaking one per frontier visit. The three handles are `Any` because
    playwright is imported lazily — its types aren't in scope at module load — and naming the slots
    here (vs. a bare 4-tuple) keeps the adjacent `browser` / `context` handles from being transposed.
    """

    pw: Any
    browser: Any
    context: Any
    page: _Page
