from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChangedFile:
    """One file a diff changed: its path and the bodies of its added/removed lines (prefix stripped).

    `binary` marks a change whose content cannot be string-matched at all — a binary hunk, or an
    untracked file that could not be read as text. Such a change carries no `lines`, yet unlike a pure
    rename (which also has no `lines`) it *is* a real content change, so it is always unattributable:
    the scan can never vouch for it, and `complete` must fall to False rather than silently pass it.
    """

    path: str
    lines: list[str]
    binary: bool = False
