"""A configured evidence-upload destination the control plane holds (BE-0110)."""

from __future__ import annotations

import dataclasses

from .object_store import ObjectStore


@dataclasses.dataclass(frozen=True)
class EvidenceTarget:
    """A configured evidence-upload destination the control plane holds (BE-0110): a credentialed
    `ObjectStore` plus the base key prefix from the ``--evidence-store`` URI. The server issues
    presigned PUT URLs against it so a worker uploads a run's evidence with no cloud credentials of
    its own; the caller appends an optional per-run prefix and the run id under *base_prefix*."""

    store: ObjectStore
    base_prefix: str  # StoreURI.prefix — empty or ends with "/"
