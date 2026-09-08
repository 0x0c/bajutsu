"""A parsed store URI: the backend, its bucket, and a key prefix."""

from __future__ import annotations

import dataclasses
from typing import Literal


@dataclasses.dataclass(frozen=True)
class StoreURI:
    """A parsed store URI: the backend, its bucket, and a key prefix.

    *prefix* is normalized to end with ``/`` (or be empty), so keys append cleanly without fusing
    (``prefix`` + ``run/x`` never yields ``prefixrun/x``)."""

    backend: Literal["s3", "gcs"]
    bucket: str
    prefix: str
