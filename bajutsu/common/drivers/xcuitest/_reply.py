"""A decoded response from the resident runner."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from bajutsu.common.drivers import base


@dataclass(frozen=True)
class _Reply:
    """A decoded runner response.

    `elements` carries the `GET /elements` payload (each item is the normalized element fields plus
    its `handle`); `png` carries raw `GET /screenshot` bytes. `raw` is the undecoded JSON body — kept
    alongside the parsed fields (not just for `/elements`; cheap, it is the same bytes already read)
    so `_query_with_handles` can hand the tree query's body to `RawSourceProvider` without a second
    round trip.
    """

    status: str
    elements: list[dict[str, Any]] | None = None
    png: bytes | None = field(default=None, repr=False)
    size: base.Point | None = None  # the `GET /screen` viewport (w, h), BE-0326
    raw: bytes | None = field(default=None, repr=False)
