"""The slice of an object-storage client the upload seams use, so a fake fits."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Protocol

from ._shared import _PUT_TTL


class ObjectStore(Protocol):
    """The slice of an object-storage client the seams use (so a fake fits): artifact reads
    (exists / get_bytes / presigned_url / list_keys), writes (put_bytes / put_file), and signed PUT
    URLs (presigned_put_url) for credential-free uploads by a worker."""

    def exists(self, key: str) -> bool:
        """Whether an object exists at *key* (without downloading it)."""

    def get_bytes(self, key: str) -> bytes | None:
        """The object's bytes at *key*, or None if absent."""

    def put_bytes(self, key: str, data: bytes, *, content_type: str = "") -> None:
        """Write *data* to the object at *key* (creating or overwriting), tagging its MIME type when
        *content_type* is given."""

    def put_file(self, key: str, path: Path, *, content_type: str = "") -> None:
        """Upload the file at *path* to *key*, streaming from disk (no full read into memory) — for
        large run artifacts like videos — tagging its MIME type when *content_type* is given."""

    def presigned_url(self, key: str) -> str:
        """A short-lived signed GET URL for *key*."""

    def presigned_put_url(self, key: str, *, content_type: str = "", ttl: int = _PUT_TTL) -> str:
        """A signed PUT URL for *key*, valid *ttl* seconds — lets a caller upload without holding
        cloud credentials. Binds *content_type* when given, so the upload must match it."""

    def list_keys(self, prefix: str) -> list[str]:
        """Every object key under *prefix*."""

    def delete_key(self, key: str) -> None:
        """Delete the object at *key*, a no-op if it is already absent (idempotent) — the write
        counterpart the run-purge path (BE-0239) needs, so a soft-deleted run's evidence can be
        permanently removed from storage."""

    def delete_keys(self, keys: Iterable[str]) -> None:
        """Delete every object in *keys* (each idempotent, per `delete_key`) — a whole run's key set
        at once when a run is purged."""
