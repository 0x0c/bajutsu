"""A screen's identity, the key the map is indexed by."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Fingerprint:
    """A screen's identity.

    `kind` is "id" (stable, identifier-derived) or "structural" (the less-stable fallback for
    screens with too few accessibility identifiers).
    """

    value: str
    kind: str
