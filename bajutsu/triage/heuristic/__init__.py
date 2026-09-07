"""M4 self-healing triage — read a failed run, diagnose it, propose a minimal fix.

The boundary holds: triage is **advisory** — it never decides pass/fail, only explains a
failure and suggests an edit a human reviews. `assemble` extracts the failure context from
a saved run (pure); a `TriageAgent` turns that into a diagnosis. The default
`HeuristicTriageAgent` is rule-based (no AI, deterministic — it doubles as the test double);
an AI agent can be dropped in behind the same protocol.
"""

from ._functions import _FIX_LABELS as _FIX_LABELS
from ._functions import (
    PickArtifact,
    apply_fix,
    apply_result,
    assemble,
    assemble_cross_run,
    cross_run_payload,
    diff_fix,
    fix_summary,
    flag_laxer,
    render,
    render_cross_run,
    result_payload,
)
from ._functions import _close as _close
from ._functions import _elements_near as _elements_near
from ._functions import _evidence_summary as _evidence_summary
from ._functions import _failed_expectations as _failed_expectations
from ._functions import _first as _first
from ._functions import _first_failed_step as _first_failed_step
from ._functions import _ids as _ids
from ._functions import _iter_models as _iter_models
from ._functions import _load_bytes as _load_bytes
from ._functions import _load_elements as _load_elements
from ._functions import _load_scenario as _load_scenario
from ._functions import _measure as _measure
from ._functions import _nearest_artifact as _nearest_artifact
from ._functions import _paired_screenshot as _paired_screenshot
from ._functions import _read_artifact as _read_artifact
from ._functions import _read_json as _read_json
from ._functions import _run_evidence as _run_evidence
from ._functions import _screenshot_near as _screenshot_near
from ._functions import _str_or_none as _str_or_none
from ._functions import _target_id as _target_id
from ._lax_metrics import _LaxMetrics as _LaxMetrics
from ._shared import FIX_KINDS
from .applied_fix import AppliedFix
from .cross_run_triage_agent import CrossRunTriageAgent
from .cross_run_triage_context import CrossRunTriageContext
from .failed_step import FailedStep
from .fix import Fix
from .heuristic_triage_agent import _ACT_TARGETS as _ACT_TARGETS
from .heuristic_triage_agent import HeuristicTriageAgent
from .run_evidence import RunEvidence
from .triage import Triage
from .triage_agent import TriageAgent
from .triage_context import TriageContext

__all__ = [
    "FIX_KINDS",
    "AppliedFix",
    "CrossRunTriageAgent",
    "CrossRunTriageContext",
    "FailedStep",
    "Fix",
    "HeuristicTriageAgent",
    "PickArtifact",
    "RunEvidence",
    "Triage",
    "TriageAgent",
    "TriageContext",
    "apply_fix",
    "apply_result",
    "assemble",
    "assemble_cross_run",
    "cross_run_payload",
    "diff_fix",
    "fix_summary",
    "flag_laxer",
    "render",
    "render_cross_run",
    "result_payload",
]
