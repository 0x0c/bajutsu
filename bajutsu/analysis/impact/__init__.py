"""Test impact analysis — the scenario steps a source change is likely to affect (BE-0321).

The reverse of the coverage map (BE-0050): where `coverage` walks the suite forward to the app
surface it exercises, this inverts the same static scenario analysis into a map from each stable id,
screen, and asserted endpoint to the `(scenario, step)` pairs that reference it. A change — read as a
`git` diff — is turned into a *touched set* by plain string match (each referenced literal tested
against the diff's added/removed lines), and joined back through the index to the affected steps.

Deterministic and app-agnostic: the same diff and scenarios always yield the same affected set, the
match needs no per-language parsing, and no model is consulted. Soundness is bounded in both
directions and the bounds are surfaced, not hidden — a change that edits no referenced literal is
*unattributable* (it maps to no reference), so the report flags itself incomplete and a full run is
warranted; a short or common literal can widen the set past the truly-affected steps (over-selection,
the safe direction for CI). Read-only and advisory, of a piece with `audit` / `coverage` / `stats`:
it never runs a scenario, never touches a device, and never gates CI (BE-0257).
"""

from ._functions import _ACTION_KEYS as _ACTION_KEYS
from ._functions import _binary_path as _binary_path
from ._functions import _diff_header_path as _diff_header_path
from ._functions import _request_literals as _request_literals
from ._functions import _step_label as _step_label
from ._functions import impact, parse_diff, render, reverse_index
from .affected_step import AffectedStep
from .changed_file import ChangedFile
from .impact import Impact
from .reference import Reference
from .reverse_index import ReverseIndex
from .step_ref import StepRef
from .touched_ref import TouchedRef

__all__ = [
    "AffectedStep",
    "ChangedFile",
    "Impact",
    "Reference",
    "ReverseIndex",
    "StepRef",
    "TouchedRef",
    "impact",
    "parse_diff",
    "render",
    "reverse_index",
]
