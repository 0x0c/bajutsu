"""The content types and URI schemes an evidence upload is written under."""

from __future__ import annotations

_PRESIGN_TTL = 900  # seconds a signed GET URL stays valid (15 min)
_PUT_TTL = (
    3600  # seconds a signed PUT URL stays valid (1 h) — long enough to upload one run's batch
)
