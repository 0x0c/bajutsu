"""Stream an uploaded zip into a confined temp file, capped and hashed as it arrives."""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

from .upload_too_large import UploadTooLarge

# Resource bounds (zip-bomb defense). Extraction aborts the moment one is crossed. Sized for a real
# bundle — a config + a scenario tree + a built ``.app``/``.ipa`` (an app bundle holds many small
# files: frameworks, assets) — with headroom, not for arbitrary archives.
MAX_UPLOAD_BYTES = 1024 * 1024 * 1024  # 1 GiB on the wire (the compressed upload)


class BoundedZipReceiver:
    """Streams an uploaded zip's bytes into a confined temp file, capped and hashed as they arrive
    (BE-0073) — the transport-agnostic core the stdlib handler's blocking ``rfile.read`` loop and the
    FastAPI async ``request.stream()`` loop both drive, so the bound + hash logic lives once instead
    of drifting between the two backends the way BE-0073's route itself once did. A caller pushes
    each chunk via ``write`` (raising ``UploadTooLarge`` the instant the cap is crossed), calls
    ``digest`` to finalize and get the hex sha256, and ``cleanup`` in a ``finally`` to remove the temp
    file — safe to call whether or not ``digest`` ran, and whether or not the caller consumed it."""

    def __init__(self, *, cap: int | None = None) -> None:
        # Read the module constant here, not as a parameter default — a default is bound once at
        # class-definition time, which would freeze the very first (real) value and put it out of a
        # test's monkeypatch reach forever.
        self._cap = MAX_UPLOAD_BYTES if cap is None else cap
        self._digest = hashlib.sha256()
        self.received = 0
        fd, name = tempfile.mkstemp(suffix=".zip")
        self._file = os.fdopen(fd, "wb")
        self.path = Path(name)

    def write(self, chunk: bytes) -> None:
        self.received += len(chunk)
        if self.received > self._cap:
            raise UploadTooLarge(f"upload too large (max {self._cap} bytes)")
        self._digest.update(chunk)
        self._file.write(chunk)

    def digest(self) -> str:
        """Close the write handle and return the hex sha256 of everything written so far."""
        self._file.close()
        return self._digest.hexdigest()

    def cleanup(self) -> None:
        """Remove the temp file. Idempotent — safe after `digest()` or on a failure path instead."""
        self._file.close()
        self.path.unlink(missing_ok=True)
