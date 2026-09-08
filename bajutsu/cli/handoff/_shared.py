"""The callback a handoff responder speaks to the user through."""

from __future__ import annotations

from collections.abc import Callable

Say = Callable[[str], None]
