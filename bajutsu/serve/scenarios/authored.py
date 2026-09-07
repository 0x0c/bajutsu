"""Where a `record` run writes the scenario it authored."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Authored:
    """Where a `record` run writes its authored scenario.

    `out` is the ``--out`` value — a trusted absolute path on the local backend (the file lands in
    the scenarios dir directly), or a workspace-relative path on the server backend. `save` is
    ``(app, ref)`` telling a remote worker to persist the authored file to per-project storage
    afterward (the run host has no shared filesystem with the control plane); None locally."""

    out: str
    save: tuple[str, str] | None = None
