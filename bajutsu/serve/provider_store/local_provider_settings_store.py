"""The single-JSON-file provider settings store — the local-serve shape."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from ._functions import decode, encode_settings
from .persisted_provider_settings import PersistedProviderSettings
from .provider_settings_error import ProviderSettingsError


class LocalProviderSettingsStore:
    """A `ProviderSettingsStore` backed by a single JSON file — the local-serve shape.

    The file is a sibling of serve's run directory; a hosted deployment wires a different,
    per-organization store instead of this one.
    """

    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> PersistedProviderSettings | None:
        if not self._path.exists():
            return None
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            raise ProviderSettingsError(f"cannot read {self._path}: {e}") from e
        return decode(raw, str(self._path))

    def save(self, data: PersistedProviderSettings) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"provider": data.provider, "settings": encode_settings(data.settings)}
        # Write-then-replace so a crash mid-write never leaves a half-written file that load()
        # would reject on the next boot. The temp name is unique per call (mkstemp) — serve is a
        # ThreadingHTTPServer, so a fixed `<path>.tmp` suffix would let two concurrent saves clobber
        # each other's in-flight write before either os.replace() lands.
        fd, tmp_name = tempfile.mkstemp(
            dir=self._path.parent, prefix=self._path.name + ".", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(json.dumps(payload, indent=2))
            Path(tmp_name).replace(self._path)
        except OSError:
            Path(tmp_name).unlink()
            raise
