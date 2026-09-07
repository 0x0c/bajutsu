"""One artifact a run produced, as the API surfaces it."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Artifact:
    content_type: str
    body: bytes | None = None  # inline bytes (local filesystem)
    redirect: str | None = None  # a signed URL to 302 to (object storage)
