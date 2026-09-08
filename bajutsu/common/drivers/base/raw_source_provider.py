"""The seam for a backend that retains that raw reply, for the `rawTree` capture kind."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .raw_source import RawSource


@runtime_checkable
class RawSourceProvider(Protocol):
    """A backend that retains the raw dump behind its last parsed tree, for the `rawTree` capture kind.

    Every coordinate-tree backend's frame computation is normally a black box once parsed into
    `Element`s: diagnosing whether a mismatch between the screen and a resolved coordinate comes from
    the device's own dump or from bajutsu's parsing of it needs the dump itself, which `_describe()`
    otherwise discards as a local variable the moment it is parsed. A backend that keeps it exposes
    this seam so `bajutsu/evidence/core.py`'s `write_raw_tree` can persist it alongside `elements.json`
    — opt-in (a scenario's `capture: [rawTree, ...]`), never in the default capture list, since it adds
    a same-sized text artifact per captured step. `AdbDriver` and `XcuitestDriver` implement it (the raw
    UI Automator dump, the raw `GET /elements` body). Not implementing this means "no raw dump to
    persist", which keeps every other backend (`FakeDriver`, Playwright) exactly as before — the same
    narrow opt-in as the protocols above (BE-0351).
    """

    def last_raw_source(self) -> RawSource | None: ...
