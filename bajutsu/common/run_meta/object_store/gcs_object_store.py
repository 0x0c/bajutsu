"""The store over one Google Cloud Storage bucket, via an injected bucket handle."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import timedelta
from pathlib import Path
from typing import Any

from ._shared import _PRESIGN_TTL, _PUT_TTL


class GCSObjectStore:
    """`ObjectStore` over one Google Cloud Storage bucket via an injected `storage.Bucket`.

    The bucket is injected (like `S3ObjectStore`'s client) so a fake drives the gate. Signed URLs use
    V4 signing, which GCS supports for both GET and PUT.

    *credentials* drives signing when the bucket's own credentials can't sign locally: a Workload
    Identity Federation credential (KSA→GSA impersonation) carries an access token but no private
    key, so local V4 signing raises. For that shape only, the SDK is told to call the IAM
    ``signBlob`` API via ``service_account_email``/``access_token`` passed to
    `generate_signed_url` instead. Left `None`, or given a credential that can already sign
    locally, signing falls back to whatever the bucket itself was built with."""

    def __init__(
        self, bucket: Any, *, presign_ttl: int = _PRESIGN_TTL, credentials: Any = None
    ) -> None:
        self._bucket = bucket
        self._ttl = presign_ttl
        self._credentials = credentials

    def _signing_kwargs(self) -> dict[str, Any]:
        # Passing service_account_email/access_token to generate_signed_url isn't a fallback —
        # it's an override that makes the SDK sign via the IAM signBlob API unconditionally,
        # skipping local signing even when the credential could do it. So this only takes that
        # path for a credential that actually needs it: a key-file or already-impersonated
        # credential implements google.auth.credentials.Signing and should keep signing locally
        # (no per-URL IAM round trip, no new serviceAccountTokenCreator grant on a deployment
        # that works today); a credential with no service_account_email (e.g. `gcloud auth
        # application-default login`) has nothing to sign as, so it's left to the SDK's own
        # local-signing attempt and its own error rather than an AttributeError from here.
        if self._credentials is None:
            return {}
        from google.auth.credentials import Signing

        email = getattr(self._credentials, "service_account_email", None)
        if email is None or isinstance(self._credentials, Signing):
            return {}
        if not self._credentials.valid:
            from google.auth.transport.requests import Request

            self._credentials.refresh(Request())
        return {"service_account_email": email, "access_token": self._credentials.token}

    def exists(self, key: str) -> bool:
        return bool(self._bucket.blob(key).exists())

    def get_bytes(self, key: str) -> bytes | None:
        blob = self._bucket.blob(key)
        if not blob.exists():
            return None
        data: bytes = blob.download_as_bytes()
        return data

    def put_bytes(self, key: str, data: bytes, *, content_type: str = "") -> None:
        kw = {"content_type": content_type} if content_type else {}
        self._bucket.blob(key).upload_from_string(data, **kw)

    def put_file(self, key: str, path: Path, *, content_type: str = "") -> None:
        kw = {"content_type": content_type} if content_type else {}
        self._bucket.blob(key).upload_from_filename(str(path), **kw)

    def presigned_url(self, key: str) -> str:
        url: str = self._bucket.blob(key).generate_signed_url(
            version="v4",
            expiration=timedelta(seconds=self._ttl),
            method="GET",
            **self._signing_kwargs(),
        )
        return url

    def presigned_put_url(self, key: str, *, content_type: str = "", ttl: int = _PUT_TTL) -> str:
        kw = {"content_type": content_type} if content_type else {}
        kw.update(self._signing_kwargs())
        url: str = self._bucket.blob(key).generate_signed_url(
            version="v4", expiration=timedelta(seconds=ttl), method="PUT", **kw
        )
        return url

    def list_keys(self, prefix: str) -> list[str]:
        return [str(b.name) for b in self._bucket.list_blobs(prefix=prefix)]

    def delete_key(self, key: str) -> None:
        # Unlike S3's idempotent delete, `blob.delete()` raises on a missing object. Delete first and
        # only re-raise if the object is *still* there afterward: that keeps the seam's "no-op if
        # absent" contract under concurrency (the retention sweep runs unlocked on every history read,
        # so two overlapping purges of the same key race here) — a plain exists()-then-delete() would
        # let the loser raise. Re-checking state avoids importing the GCS SDK's exception type too
        # (the default gate path stays SDK-free, #117 import guard).
        blob = self._bucket.blob(key)
        try:
            blob.delete()
        except (
            Exception
        ):  # narrowed by the exists() re-check: a real error leaves the object present
            if blob.exists():
                raise

    def delete_keys(self, keys: Iterable[str]) -> None:
        for key in keys:
            self.delete_key(key)
