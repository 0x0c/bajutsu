"""The current-screen read a condition wait needs, narrower than a whole `Driver`."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .element import Element

# --- Shared driver-side helpers (hoisted from the drivers to defeat per-backend drift, BE-0251) ---


@runtime_checkable
class Queryable(Protocol):
    """Just the current-screen read a wait needs — the query surface, not a full `Driver`.

    `default_wait_for` reads one screen and matches; a shared read base like `CoordinateTreeDriver`
    supplies exactly that without implementing the whole actuator surface, so typing the helper to
    this narrow protocol lets both a full `Driver` and such a base delegate to it.
    """

    def query(self) -> list[Element]: ...
