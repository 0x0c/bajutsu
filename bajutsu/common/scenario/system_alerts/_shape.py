"""One rendering of a prompt in one language: how to recognize it, and what each choice taps."""

from __future__ import annotations

from typing import TypedDict


class _Shape(TypedDict):
    """One rendering of a prompt in one language: how to recognize it, and what each choice taps.

    A prompt renders as more than one shape when the operating system varies its buttons by context
    or by version — `savePassword` does both. `identifying` is every label that must be present for
    this shape to be the alert on screen; `excludes` is the labels whose presence rules it out, for
    a shape another alert's button set would otherwise satisfy. A `TypedDict` so mypy, not a runtime
    check, rejects a half-filled entry — one that would resolve `deny` while `grant` raised a
    `KeyError` mid-run.
    """

    identifying: tuple[str, ...]
    grant: str
    deny: str
    excludes: tuple[str, ...]
