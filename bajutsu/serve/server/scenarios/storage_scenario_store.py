from __future__ import annotations

from .scenario_storage import ScenarioStorage
from .storage_scenario_scope import StorageScenarioScope


class StorageScenarioStore:
    """Resolves a project (app) to its storage-backed scenario scope (the ScenarioStore seam)."""

    def __init__(self, storage: ScenarioStorage) -> None:
        self._storage = storage

    def scope(
        self, app: str | None, *, session: str | None = None, org: str = ""
    ) -> StorageScenarioScope | None:
        # The pair is carried to the scope rather than consumed here: whether it matters depends on
        # the storage behind it. A purely object-storage backend addresses scenarios by name within
        # the org's prefix and ignores it; the local-tree one reads from the bound configuration's own
        # tree, which is per session (BE-0393 unit 2).
        if not app or not self._storage.has_app(app, session=session, org=org):
            return None
        return StorageScenarioScope(self._storage, app, session=session, org=org)
