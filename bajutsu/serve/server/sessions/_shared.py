"""The key prefixes and lifetimes a stored session is written under."""

from __future__ import annotations

_DEFAULT_TTL = 604800  # seconds a session lives before Redis evicts it (7 days)
