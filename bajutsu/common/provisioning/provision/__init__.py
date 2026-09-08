"""Config-aware environment installer (BE-0164).

Reads a project's effective config, resolves which backends its ``targets.*`` actually use and
whether an AI provider is configured, and installs exactly the pip extras and external tools those
need — not "every backend unconditionally" and not "everything". A local, developer-invoked bootstrap step:
it never runs on a hosted or uploaded-config path (the boundary BE-0090 closed), runs before any
scenario, and is never part of a pass/fail decision (prime directive #1).

``plan`` is pure (config -> ``InstallPlan``) so it is unit-testable without touching the machine;
``provision`` executes a plan idempotently, shelling out only for tools that are actually missing.
Both read their facts from the one ``requirements`` mapping shared with ``preflight``, so a new
backend plugs in there rather than forking this installer (prime directive #3).
"""

from ._functions import Runner, System, Which, main, plan, plan_for_backends, provision
from ._functions import _ai_configured as _ai_configured
from ._functions import _build as _build
from ._functions import _echo as _echo
from ._functions import _load as _load
from ._functions import _resolved_actuators as _resolved_actuators
from ._functions import _run as _run
from ._functions import _tool_action as _tool_action
from ._functions import _unique as _unique
from ._functions import _unique_tools as _unique_tools
from .install_plan import InstallPlan
from .provision_report import ProvisionReport

__all__ = [
    "InstallPlan",
    "ProvisionReport",
    "Runner",
    "System",
    "Which",
    "main",
    "plan",
    "plan_for_backends",
    "provision",
]
