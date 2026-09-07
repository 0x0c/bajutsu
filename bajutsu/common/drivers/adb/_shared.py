"""The resource-id shapes and logger the Android driver reads the device through."""

from __future__ import annotations

import logging

# The four accessibility fields that name one already-chosen element to the resident server:
# `resource-id`, `content-desc`, `text`, `class`, verbatim from the dump.
NodeIdentity = tuple[str, str, str, str]

logger = logging.getLogger("bajutsu.adb.resident")
