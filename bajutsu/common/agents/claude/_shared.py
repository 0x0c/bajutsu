"""The tool schemas and prompt fragments the Claude authoring agent is built from."""

from __future__ import annotations

from typing import Any

# A reusable selector fragment: address an element by id (preferred), else by any combination
# of label / value / traits, with index as a last-resort disambiguator. Shared by every tool so
# id-first and label-only apps use one shape. The conditions are ANDed at resolve time.
_TARGET_PROPS: dict[str, Any] = {
    "id": {"type": "string", "description": "accessibility identifier (preferred when present)"},
    "label": {"type": "string", "description": "exact accessibility label (when there is no id)"},
    "value": {
        "type": "string",
        "description": "exact accessibility value — e.g. a text field's placeholder ('Email') "
        "while it is empty, or a status text's value",
    },
    "traits": {
        "type": "array",
        "items": {"type": "string"},
        "description": "required traits, e.g. ['button'] or ['textField'] — narrows an unlabeled element",
    },
    "index": {"type": "integer", "description": "0-based pick among elements that still match"},
}

# The agent's reasoning for the turn — required on every tool so the watcher always sees a
# thought (it is streamed live during `record`), not just the chosen action.
_REASON_PROP: dict[str, Any] = {
    "reason": {
        "type": "string",
        "description": "one short sentence of your reasoning for this turn: what you see and "
        "why this action advances the goal",
    }
}

# Which planned step this action carries out — surfaced live so the watcher sees the run's place in
# the plan. Optional: omit when there is no plan (`Observation.plan` empty) or the move fits none.
_PLAN_PROP: dict[str, Any] = {
    "plan_step": {
        "type": "integer",
        "description": "the 1-based number of the planned step (from the plan shown this turn) that "
        "this action carries out; omit when there is no plan",
    }
}
