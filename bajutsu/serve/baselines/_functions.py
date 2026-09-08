"""Validate a baseline name before it reaches the filesystem."""

from __future__ import annotations

from pathlib import PurePosixPath


def _safe_baseline_name(name: str) -> bool:
    """Whether *name* is an obviously safe baseline name: non-empty, NUL-free, relative, no ``..``
    traversal. The store still does full containment on top; this is the shared first guard."""
    if not name or "\x00" in name:
        return False
    pure = PurePosixPath(name.replace("\\", "/"))
    return not pure.is_absolute() and ".." not in pure.parts
