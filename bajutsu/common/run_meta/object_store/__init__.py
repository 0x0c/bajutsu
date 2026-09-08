"""Object storage: a backend-agnostic `ObjectStore` and a single-URI selector.

A store is addressed by one URI — ``s3://bucket/prefix`` or ``gs://bucket/prefix`` — so the
destination (and thus the cloud lifecycle policy that governs retention) is a single, greppable
string. `parse_store_uri` splits it into a `StoreURI`; `object_store_from_uri` builds the matching
`ObjectStore`; `store_target_from_uri` bundles both into a (store, prefix) pair. This one seam backs
two independent settings that each resolve their own URI: run evidence upload (``--evidence-store``,
BE-0110, via `evidence_target_from_uri`/`EvidenceTarget`) and the server backend's own artifact/
scenario/baseline storage (``BAJUTSU_SERVER_STORE``, BE-0204, via ``serve/server/object_store.py``).
Both S3 (boto3) and GCS (google-cloud-storage) SDKs are imported **lazily**, so this module is safe
to import without either extra and the default CLI/serve path stays SDK-free (the #117 import guard).

`ObjectStore` and `S3ObjectStore` were promoted here from ``serve/server/object_store.py`` (which now
re-exports them) so both ``run`` and ``serve`` share one seam.
"""

from ._functions import _CONTENT_TYPES as _CONTENT_TYPES
from ._functions import _MIME as _MIME
from ._functions import _NOT_FOUND as _NOT_FOUND
from ._functions import _SCHEME_BACKEND as _SCHEME_BACKEND
from ._functions import _content_type as _content_type
from ._functions import _is_not_found as _is_not_found
from ._functions import (
    content_type_for,
    evidence_target_from_uri,
    object_store_from_uri,
    parse_store_uri,
    store_target_from_uri,
    upload_tree,
)
from ._shared import _PRESIGN_TTL as _PRESIGN_TTL
from ._shared import _PUT_TTL as _PUT_TTL
from .evidence_target import EvidenceTarget
from .gcs_object_store import GCSObjectStore
from .object_store import ObjectStore
from .s3_object_store import S3ObjectStore
from .store_uri import StoreURI
from .upload_summary import UploadSummary

__all__ = [
    "EvidenceTarget",
    "GCSObjectStore",
    "ObjectStore",
    "S3ObjectStore",
    "StoreURI",
    "UploadSummary",
    "content_type_for",
    "evidence_target_from_uri",
    "object_store_from_uri",
    "parse_store_uri",
    "store_target_from_uri",
    "upload_tree",
]
