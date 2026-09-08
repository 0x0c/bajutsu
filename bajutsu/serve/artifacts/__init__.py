"""The ArtifactStore seam: how a run's artifacts are read back (BE-0015 local/server parity).

A run writes its tree under ``runs/<id>/`` (report.html, screenshots, manifest.json, …). Serving
those back is the one point where local and server hosting diverge: the local store reads files
**confined to ``runs_dir``** (`LocalArtifactStore`), while the server store (`ObjectStorageArtifactStore`)
fetches from object storage or hands back a signed-URL redirect. Keeping the path-containment in one
place means a crafted ``rel`` can never escape ``runs_dir``, and a server store gets the same
guarantee by never touching the filesystem at all.
"""

from .artifact import Artifact
from .artifact_store import ArtifactStore
from .local_artifact_store import _DELETED_MARKER as _DELETED_MARKER
from .local_artifact_store import _TRASH as _TRASH
from .local_artifact_store import LocalArtifactStore

__all__ = ["Artifact", "ArtifactStore", "LocalArtifactStore"]
