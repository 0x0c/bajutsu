"""The seam a run's artifacts are read back through."""

from __future__ import annotations

from typing import Any, Protocol

from .artifact import Artifact


class ArtifactStore(Protocol):
    """Reads back the artifacts a run produced."""

    def get(self, rel: str) -> Artifact | None:
        """Serve run-relative path *rel*, or None if it's missing or escapes the run tree."""

    def open_bytes(self, rel: str) -> bytes | None:
        """Raw bytes for run-relative path *rel* (e.g. a visual baseline), or None."""

    def exists(self, rel: str) -> bool:
        """Whether run-relative path *rel* is present (and doesn't escape the run tree).

        A HEAD-style probe for callers that only need to decide whether to link to an artifact
        (e.g. an editor's per-step ``elementsUrl``/``screenshotUrl``), not read its bytes — cheap
        on both backends, unlike keying off `get`/`open_bytes` returning non-None (BE-0258)."""

    def list_runs(self) -> list[dict[str, Any]]:
        """Past runs, newest first, each summarized for the history list."""

    def list_crawl_runs(self) -> list[dict[str, Any]]:
        """Past crawl runs, newest first, each summarized from its screenmap.json (BE-0180/BE-0190).

        The crawl-history counterpart to `list_runs`: keyed on screenmap.json (the artifact every
        crawl streams) instead of manifest.json (a crawl has no pass/fail verdict). Each entry is the
        `helpers.crawl_run_summary` shape the Crawl tab consumes."""

    def render_report(self, run_id: str) -> Artifact | None:
        """Render *run_id*'s report.html **on view** from its stored model with the current template
        (BE-0068). None when the report can't be rendered — the run is missing, has no manifest, the
        model can't be loaded (malformed manifest/scenario), or this store doesn't render on view —
        so the caller falls back to the baked file. Returning fresh HTML means an upgraded serve
        refreshes every report with no per-run re-bake; the baked file is then a cache/export."""

    def archive(self, run_id: str) -> Artifact | None:
        """A zip of the whole run *run_id* (rooted under `<run_id>/`), or None if it's missing
        or *run_id* escapes the run tree — the download/export half of the report (BE-0060)."""

    def soft_delete_run(self, run_id: str) -> bool:
        """Move *run_id* to the trash so it drops out of the history lists but stays restorable
        within the retention window (BE-0239). True when a live run was trashed, False when there
        was none (a bad/absent id). Not destructive — `purge_run` is the irreversible step."""

    def restore_run(self, run_id: str) -> bool:
        """Undo `soft_delete_run` for *run_id*, returning it to the history lists (BE-0239). True
        when a trashed run was restored, False when none was trashed (or a live run already holds
        the id)."""

    def purge_run(self, run_id: str) -> bool:
        """Permanently remove *run_id*'s bytes — trashed or live (the ``?purge=true`` immediate
        path) — the one irreversible step (BE-0239). True when anything was removed."""

    def list_trashed_runs(self) -> list[dict[str, Any]]:
        """Soft-deleted runs as ``{"id", "deletedAt"}`` (``deletedAt`` an ISO-8601 UTC string, or
        None if unknown), for the retention sweep (BE-0239). Newest-deleted first."""
