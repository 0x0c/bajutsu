"""A storage-backed ScenarioStore for the hosted backend (BE-0015 server phase).

`LocalScenarioStore` resolves an app to a scenarios dir on disk. `StorageScenarioStore` keeps the
same `ScenarioStore` seam but resolves a scenario **by name within a project, from per-project
storage** — never from a client-chosen filesystem path, which is the arbitrary-path-execution
guard (BE-0051) made structural: no path ever exists on the control plane.

It serves the authoring operations the UI needs — ``list`` / ``read`` / ``save`` — by delegating to
an injected `ScenarioStorage` (a DB / object store; real backing arrives with the persistence
slice). ``runnable`` returns the scenario as **materials** (the text plus a workspace-relative
path) so a remote worker writes it before running — no path ever exists on the control plane.
``out_path`` (record's authoring output) is still worker-side and not served yet.

This module imports no storage SDK — `ScenarioStorage` is injected — so it's unit-tested with a
fake and the default path stays server-free (the import guard).
"""

from .local_tree_scenario_storage import LocalTreeScenarioStorage
from .local_tree_scenario_storage import _logger as _logger
from .object_scenario_storage import ObjectScenarioStorage
from .scenario_storage import ScenarioStorage
from .storage_scenario_scope import _WORKSPACE_SCENARIOS as _WORKSPACE_SCENARIOS
from .storage_scenario_scope import StorageScenarioScope
from .storage_scenario_store import StorageScenarioStore

__all__ = [
    "LocalTreeScenarioStorage",
    "ObjectScenarioStorage",
    "ScenarioStorage",
    "StorageScenarioScope",
    "StorageScenarioStore",
]
