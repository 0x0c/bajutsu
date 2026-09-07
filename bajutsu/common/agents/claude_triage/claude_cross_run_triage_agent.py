"""The cross-run triage agent backed by Claude: ask why one scenario intermittently flips."""

from __future__ import annotations

from bajutsu.common.agents.ai_config import AiConfig
from bajutsu.common.agents.claude_backed import ClaudeBackedAgent
from bajutsu.common.ai import AiBackend, ToolDef
from bajutsu.common.ai.prompts import NEVER_JUDGE_BOUNDARY
from bajutsu.common.evidence.redaction import Redactor
from bajutsu.triage.heuristic import FIX_KINDS, CrossRunTriageContext, Triage

from ._functions import _cross_run_user_content, _forced_diagnose, _to_triage
from ._shared import MODEL

# --- cross-run flaky triage (BE-0220 Half 2) ---

# The intermittency root causes — a different axis from the single-run categories above. A flaky
# scenario fails not because one run went wrong but because something VARIES between its runs.
_CROSS_RUN_CATEGORIES = (
    "selector-ambiguity",  # a selector resolved to one element in some runs, several in others
    "timing",  # a wait/assertion raced asynchronous UI — it won some runs, lost others
    "network-variance",  # a backend response varied between runs (latency, payload, error)
    "state-leak",  # leftover state from a prior run changed the starting conditions
    "unknown",  # the cross-run evidence does not support any of the above
)

CROSS_RUN_SYSTEM_PROMPT = f"""You are an iOS end-to-end test flakiness investigator. One \
deterministic test scenario ran many times against an app on the iOS Simulator at a FIXED content \
fingerprint (its definition never changed), yet its verdict flips: some runs pass, some fail. \
Explain WHY it is intermittent and propose the minimal fix that makes it deterministic again.

You are advisory only — you diagnose and suggest. {NEVER_JUDGE_BOUNDARY} Reason strictly from \
the evidence given: for the failing runs and the passing runs, the failure message, the failed \
step, and the accessibility element tree captured nearest the failure (failing) or the run's end \
(passing), plus the scenario definition. The signal is the DELTA — what differs between a run that \
passed and one that failed under the same definition. Never invent element ids.

Call the `diagnose` tool exactly once with:
- category, one of:
  - selector-ambiguity: a selector resolved to exactly one element in some runs but matched \
several (or none) in others — the screen's element set varies.
  - timing: a wait or assertion raced asynchronous UI — the element/condition was reachable but \
present only after a delay that some runs beat and others did not.
  - network-variance: a backend response varied between runs (latency, payload, or an error) and \
the scenario did not wait for or tolerate the variation.
  - state-leak: state left by a previous run changed the starting conditions of the later ones.
  - unknown: the evidence does not support any of the above.
- summary: one or two sentences naming the concrete cause of the INTERMITTENCY (contrast a pass \
with a fail), not a single run's failure.
- suggestions: concrete, minimal edits that remove the non-determinism (disambiguate a selector \
with `within`/`index`, add or lengthen an explicit `wait`, wait on the varying condition). Prefer \
the smallest change that makes the scenario deterministic.
- fix (an automatically-applicable edit; include ONLY when you are confident, else omit). `find` \
MUST be an exact substring of the scenario definition shown below, and `replace` is what it \
becomes:
  - renameId: a selector id that should be corrected. find = the id now, replace = the correct id.
  - addIndex: an ambiguous selector. find = the exact selector fragment of the flaky step, \
replace = the same fragment with `index:` (or `within:`) added to pick one deterministically.
  - raiseTimeout: a wait that some runs lost. find = the exact `timeout: N` fragment, replace = \
it with a larger number.
Omit `fix` whenever you cannot name an exact `find` fragment. Do NOT weaken an assertion to make \
the test pass — never drop an `expect`, loosen a value/label match, or widen a selector past \
uniqueness."""

# Same shape as `TOOLS`, but the category enum is the cross-run set. The fix kinds are unchanged —
# BE-0220 Half 2 keeps the constrained BE-0023 fix set; a full YAML rewrite is a later unit.
CROSS_RUN_TOOLS: list[ToolDef] = [
    ToolDef(
        name="diagnose",
        description="Report the root cause of the scenario's intermittency and the minimal fix.",
        input_schema={
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "one or two sentences naming the cause of the intermittency",
                },
                "category": {"type": "string", "enum": list(_CROSS_RUN_CATEGORIES)},
                "suggestions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "concrete, minimal edits that remove the non-determinism",
                },
                "fix": {
                    "type": "object",
                    "description": "an automatically-applicable edit; `find` MUST be an exact "
                    "substring of the scenario definition shown",
                    "properties": {
                        "kind": {
                            "type": "string",
                            "enum": list(FIX_KINDS),
                            "description": "renameId, addIndex (disambiguate), raiseTimeout",
                        },
                        "find": {
                            "type": "string",
                            "description": "exact text in the scenario to replace",
                        },
                        "replace": {"type": "string", "description": "the replacement text"},
                    },
                    "required": ["kind", "find", "replace"],
                },
            },
            "required": ["summary", "category", "suggestions"],
        },
    ),
]


class ClaudeCrossRunTriageAgent(ClaudeBackedAgent):
    """CrossRunTriageAgent implementation that asks Claude to diagnose intermittency via forced tool use.

    The Half-2 counterpart to `ClaudeTriageAgent`: same forced-`diagnose` boundary and the same
    advisory `Triage` output, but it reasons over a `CrossRunTriageContext` (a flaky scenario's
    passing and failing runs) and classifies the intermittency's cause (BE-0220).
    """

    def __init__(
        self,
        backend: AiBackend | None = None,
        model: str | None = None,
        max_tokens: int = 1024,
        *,
        ai: AiConfig | None = None,
        redactor: Redactor | None = None,
    ) -> None:
        super().__init__(
            backend=backend, ai=ai, default_model=MODEL, model=model, redactor=redactor
        )
        self._max_tokens = max_tokens

    def triage_flaky(self, context: CrossRunTriageContext) -> Triage:
        response = _forced_diagnose(
            self._ensure_backend(),
            _cross_run_user_content(context, self._redactor),
            system=CROSS_RUN_SYSTEM_PROMPT,
            tools=CROSS_RUN_TOOLS,
            model=self._model,
            max_tokens=self._max_tokens,
            ai=self._ai,
        )
        return _to_triage(response, _CROSS_RUN_CATEGORIES)
