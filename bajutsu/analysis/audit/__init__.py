"""Static determinism audit for a scenario — a device-free, AI-free stability score.

The deterministic counterpart to flakiness tolerance (BE-0049): instead of absorbing instability,
this *grades* it. It walks a scenario without a device and scores each selector on the stability
ladder ([selectors.md](../docs/selectors.md)) — a unique `id` beats `label`/`traits`, which beat
`index`/raw coordinates — flags `wait`s gated on an over-loose condition, and flags coordinate
gestures a stable `id` could replace. It is purely observational: no model is consulted, the
scenario is never run, and the verdict / CI gate is never touched.
"""

from ._functions import _LOOSE_UNTIL as _LOOSE_UNTIL
from ._functions import _assertion_selectors as _assertion_selectors
from ._functions import _describe as _describe
from ._functions import _grade as _grade
from ._functions import _history as _history
from ._functions import _located_selectors as _located_selectors
from ._functions import _selector_finding as _selector_finding
from ._functions import _selector_ids as _selector_ids
from ._functions import _selector_match_ids as _selector_match_ids
from ._functions import _step_findings as _step_findings
from ._functions import _step_selectors as _step_selectors
from ._functions import _tier as _tier
from ._functions import _verdicts as _verdicts
from ._functions import _with_nested as _with_nested
from ._functions import (
    audit_scenario,
    canonical_os,
    classify_stability,
    longitudinal,
    referenced_ids,
    render,
    render_longitudinal,
    render_repeat,
    repeat_diff,
    scenario_matchable_ids,
    step_matchable_ids,
    unknown_os_note,
)
from .audit_report import AuditReport
from .finding import Finding
from .longitudinal_report import LongitudinalReport
from .repeat_report import RepeatReport
from .scenario_history import ScenarioHistory

__all__ = [
    "AuditReport",
    "Finding",
    "LongitudinalReport",
    "RepeatReport",
    "ScenarioHistory",
    "audit_scenario",
    "canonical_os",
    "classify_stability",
    "longitudinal",
    "referenced_ids",
    "render",
    "render_longitudinal",
    "render_repeat",
    "repeat_diff",
    "scenario_matchable_ids",
    "step_matchable_ids",
    "unknown_os_note",
]
