"""Open a store from its URI and walk a run's evidence tree into it."""

from __future__ import annotations

import mimetypes
import os
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from .evidence_target import EvidenceTarget
from .gcs_object_store import GCSObjectStore
from .object_store import ObjectStore
from .store_uri import StoreURI
from .upload_summary import UploadSummary

# S3/R2 error codes that mean "no such object" — treated as absent; anything else is surfaced.
_NOT_FOUND = frozenset({"404", "NoSuchKey", "NotFound"})

# Built from the stdlib defaults only — `MimeTypes()` never reads the OS `knownfiles`, unlike the
# module-level `mimetypes.guess_type`. See `content_type_for` for why that matters.
_MIME = mimetypes.MimeTypes()
# The extensions a run tree uploads where the OS database disagrees with the stdlib map, or where
# neither has an answer. Everything else (.png/.html/.json/.txt/.md/.mp4/.webm/.zip/…) agrees.
_CONTENT_TYPES = {
    ".xml": "application/xml",  # stdlib says text/xml; RFC 7303 prefers this, as do the OS tables
    ".log": "text/plain",
    ".yaml": "application/yaml",
    ".yml": "application/yaml",
}


# The URI scheme the caller writes → the backend name. ``gs`` follows the gsutil/gcloud convention
# while the backend name matches the library (google-cloud-storage → "gcs").
_SCHEME_BACKEND: dict[str, Literal["s3", "gcs"]] = {"s3": "s3", "gs": "gcs"}


def _is_not_found(error: Any) -> bool:
    return str(error.response.get("Error", {}).get("Code", "")) in _NOT_FOUND


def parse_store_uri(uri: str) -> StoreURI:
    """Parse a store URI (``s3://bucket/prefix`` or ``gs://bucket/prefix``) into a `StoreURI` — the
    shared shape every store-selecting setting parses (``--evidence-store``, ``BAJUTSU_SERVER_STORE``).
    ``gs://`` is supported alongside ``s3://`` (BE-0204).

    The first path segment is the bucket; the remainder is the key prefix, normalized to a trailing
    ``/`` (empty when the URI names only a bucket).

    Raises:
        ValueError: the scheme isn't ``s3`` / ``gs``, or the bucket is missing.
    """
    scheme, sep, rest = uri.partition("://")
    if not sep or scheme not in _SCHEME_BACKEND:
        raise ValueError(
            f"unsupported store URI {uri!r}: use s3://bucket/prefix or gs://bucket/prefix"
        )
    bucket, _, raw_prefix = rest.partition("/")
    if not bucket:
        raise ValueError(f"store URI {uri!r} is missing a bucket name")
    # Strip leading slashes (an extra `/` after the bucket, e.g. `s3://b//evidence/`) so keys never
    # start with `/` — a leading slash makes an empty-named segment and defeats prefix lifecycle rules.
    raw_prefix = raw_prefix.lstrip("/")
    prefix = raw_prefix if (not raw_prefix or raw_prefix.endswith("/")) else raw_prefix + "/"
    return StoreURI(backend=_SCHEME_BACKEND[scheme], bucket=bucket, prefix=prefix)


def object_store_from_uri(uri: StoreURI) -> ObjectStore:
    """Build the `ObjectStore` a `StoreURI` names, using the standard credential chain of its SDK.

    Raises:
        ImportError: the backend's optional dependency isn't installed — the message names the exact
            ``uv sync --extra …`` to run.
    """
    if uri.backend == "s3":
        try:
            import boto3
        except ImportError as e:
            raise ImportError(
                "the s3:// store needs boto3 — install it with `uv sync --extra s3`"
            ) from e
        client = boto3.client(
            "s3",
            endpoint_url=os.environ.get("BAJUTSU_S3_ENDPOINT") or None,
            region_name=os.environ.get("BAJUTSU_S3_REGION") or os.environ.get("AWS_REGION") or None,
        )
        # Imported in the body, not at module load: the store calls `_is_not_found` from this
        # module, and rule 5 breaks the cycle the split creates on the factory's single edge.
        from .s3_object_store import S3ObjectStore

        return S3ObjectStore(client, uri.bucket)
    try:
        import google.auth
        from google.cloud import storage
    except ImportError as e:
        raise ImportError(
            "the gs:// store needs google-cloud-storage — install it with `uv sync --extra gcs`"
        ) from e
    # ADC is resolved once here (not left to storage.Client()'s own default) so the same credentials
    # object backs both the client and signing — required when it's a Workload Identity Federation
    # credential (KSA→GSA impersonation) with no private key, per GCSObjectStore's docstring.
    # cloud-platform is requested explicitly: it's a superset of storage.Client's own devstorage
    # scopes *and* covers the IAM signBlob call that signing makes, so one scope serves both call
    # sites — and passing it up front keeps storage.Client's with_scopes_if_required from silently
    # swapping in a devstorage-only copy that then can't authorize signBlob.
    credentials, project = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    # storage.Client distinguishes an omitted project (falls back to its own resolution: the
    # credential, then env/gcloud/metadata) from an explicit project=None (opts into its
    # anonymous no-project mode) — so a falsy project from google.auth.default() must be left
    # out entirely, never forwarded as None.
    client = storage.Client(credentials=credentials, **({"project": project} if project else {}))
    return GCSObjectStore(client.bucket(uri.bucket), credentials=credentials)


def store_target_from_uri(uri: str) -> tuple[ObjectStore, str]:
    """Parse *uri* and build its (`ObjectStore`, key-prefix) pair — the shared "URI → store"
    resolution every store-selecting setting uses (``--evidence-store`` via `evidence_target_from_uri`
    below, and the server's ``BAJUTSU_SERVER_STORE`` (BE-0204) directly), so a second caller never
    needs to re-derive `parse_store_uri` + `object_store_from_uri` by hand.

    Raises:
        ValueError: the URI is malformed (see `parse_store_uri`).
        ImportError: the backend's optional SDK is missing (see `object_store_from_uri`).
    """
    parsed = parse_store_uri(uri)
    return object_store_from_uri(parsed), parsed.prefix


def evidence_target_from_uri(uri: str) -> EvidenceTarget:
    """Build an `EvidenceTarget` from an ``--evidence-store`` URI (parse it, then construct the store).

    Raises:
        ValueError: the URI is malformed (see `parse_store_uri`).
        ImportError: the backend's optional SDK is missing (see `object_store_from_uri`).
    """
    store, prefix = store_target_from_uri(uri)
    return EvidenceTarget(store=store, base_prefix=prefix)


def content_type_for(name: str) -> str:
    """The MIME type inferred from *name*'s extension, defaulting to ``application/octet-stream``.

    The value must be **identical on every host**: the control plane signs it into a presigned PUT
    URL and a worker on another machine sends it back as ``Content-Type``, so a difference is a
    403 ``SignatureDoesNotMatch`` rather than a cosmetic one. That rules out the module-level
    `mimetypes.guess_type`, whose answer depends on the OS MIME database (``/etc/mime.types`` and
    friends override the stdlib map: ``.xml`` reads ``application/xml`` on a full distro and
    ``text/xml`` in a slim container). `_MIME` is built from the stdlib defaults alone, and
    `_CONTENT_TYPES` pins the extensions where hosts disagree or the stdlib has no answer.
    """
    suffix = PurePosixPath(name).suffix.lower()
    if suffix in _CONTENT_TYPES:
        return _CONTENT_TYPES[suffix]
    guessed, _ = _MIME.guess_type(name)
    return guessed or "application/octet-stream"


def _content_type(path: Path) -> str:
    return content_type_for(path.name)


def upload_tree(store: ObjectStore, root: Path, prefix: str) -> UploadSummary:
    """Upload every file under *root* to *store*, keyed ``<prefix><root-name>/<relative-path>``.

    Mirrors the run's local directory layout under the prefix (so
    ``runs/<id>/00-login/after.png`` becomes ``<prefix><id>/00-login/after.png``). Symlinks and
    non-files are skipped (a symlink can't exfiltrate a path outside the tree), and each resolved
    path is confirmed inside *root* before upload. A per-file failure is collected into the returned
    `UploadSummary`, never raised — the run verdict is already final. Upload order is unspecified
    (the walk streams the generator rather than materializing/sorting it, so memory stays bounded on
    a large evidence tree) — order is irrelevant for a post-verdict side effect.

    *prefix* is normalized to a trailing ``/`` (empty stays empty) so keys nest under it rather than
    fusing (``evidence/main`` + ``<id>`` never yields ``evidence/main<id>``), even if a caller passes
    a non-normalized value — `StoreURI.prefix` already ends with ``/``, but the helper is public.
    """
    if prefix and not prefix.endswith("/"):
        prefix += "/"
    root = root.resolve()
    uploaded = 0
    failures: list[tuple[str, str]] = []
    for path in root.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        resolved = path.resolve()
        if not resolved.is_relative_to(root):
            continue
        rel = resolved.relative_to(root).as_posix()
        key = f"{prefix}{root.name}/{rel}"
        try:
            store.put_file(key, resolved, content_type=_content_type(resolved))
        except Exception as e:  # any upload error is reported, never fatal to the run
            failures.append((key, str(e)))
        else:
            uploaded += 1
    return UploadSummary(uploaded=uploaded, failures=failures)
