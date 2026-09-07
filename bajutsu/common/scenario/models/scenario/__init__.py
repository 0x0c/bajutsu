"""The top-level shapes a scenario file is made of.

Preconditions, the alert-guard control, the scenario and its reusable component, and the
scenario-file wrapper that ties them together.
"""

from ._functions import _coerce_system_alert_handling as _coerce_system_alert_handling
from .component import Component
from .preconditions import Preconditions
from .scenario import _PERMISSION_ACTIONS as _PERMISSION_ACTIONS
from .scenario import Scenario, SystemAlertHandlingField
from .scenario_file import SCHEMA_VERSION, ScenarioFile
from .system_alert_handling import SystemAlertHandling
from .system_alert_rule import SystemAlertRule

__all__ = [
    "SCHEMA_VERSION",
    "Component",
    "Preconditions",
    "Scenario",
    "ScenarioFile",
    "SystemAlertHandling",
    "SystemAlertHandlingField",
    "SystemAlertRule",
]
