"""Whether a point hit its element, and what covered it if not."""

from __future__ import annotations

from typing import NamedTuple

from bajutsu.common.drivers import base


class _HitResult(NamedTuple):
    """`_point_hits`'s verdict: whether the point hit `el`, and what covered it if not.

    `cover` / `rect` name the covering element the same way `base.raise_if_covered` names a cover on
    the other backends; both are `None` together on a hit, or when nothing rendered at the point at
    all (BE-0349).
    """

    ok: bool
    cover: str | None
    rect: base.Frame | None
