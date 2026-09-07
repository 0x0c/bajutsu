"""The HTTP file transfer seam the submitter uses against Device Farm's presigned URLs."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class Transfer(Protocol):
    """The HTTP file transfer the submitter uses against Device Farm's presigned S3 URLs."""

    def upload(self, url: str, path: Path) -> None:
        """PUT the file at `path` to the presigned `url`."""
        raise NotImplementedError

    def download(self, url: str) -> bytes:
        """Fetch and return the raw bytes of the artifact at `url` (dispatch is `_store_artifact`)."""
        raise NotImplementedError
