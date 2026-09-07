"""The ScenarioStore seam: how a scenario is resolved, listed, read, and written (BE-0015).

Scenario resolution is the most security-sensitive serve surface: a client must never be able to
run or read an arbitrary file path on the host (BE-0051). `ScenarioStore` is the one point where
this diverges between local and server hosting: the local store confines everything to the app's
scenarios dir on disk (`LocalScenarioStore`), while the server store fetches by id from
per-project storage — where a path never exists, so arbitrary-path execution is impossible by
construction. The containment and the `runnable` guard live here, in one place.
"""

from .authored import Authored
from .local_scenario_scope import LocalScenarioScope
from .local_scenario_store import LocalScenarioStore
from .runnable import Runnable
from .scenario_scope import ScenarioScope
from .scenario_store import ScenarioStore

__all__ = [
    "Authored",
    "LocalScenarioScope",
    "LocalScenarioStore",
    "Runnable",
    "ScenarioScope",
    "ScenarioStore",
]
