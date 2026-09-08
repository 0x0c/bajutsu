"""The image part of a user message — raw bytes plus its media type."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ImagePart:
    """An image part of a user message — raw bytes plus its media type.

    Held as raw bytes (not base64) so the neutral layer never carries a vendor's encoding; the
    adapter encodes as the provider requires. Images cannot be redacted (BE-0047), so they reach
    only the user-configured endpoint unchanged.
    """

    data: bytes
    media_type: str = "image/png"
