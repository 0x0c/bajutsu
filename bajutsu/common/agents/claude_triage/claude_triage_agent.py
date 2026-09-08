"""The triage agent backed by Claude: ask the model for a diagnosis through forced tool use."""

from __future__ import annotations

from bajutsu.common.agents.ai_config import AiConfig
from bajutsu.common.agents.claude_backed import ClaudeBackedAgent
from bajutsu.common.ai import AiBackend, ToolDef
from bajutsu.common.ai.prompts import NEVER_JUDGE_BOUNDARY
from bajutsu.common.evidence.redaction import Redactor
from bajutsu.triage.heuristic import FIX_KINDS, Triage, TriageContext

from ._functions import _CATEGORIES, _forced_diagnose, _to_triage, _user_content
from ._shared import MODEL

SYSTEM_PROMPT = f"""You are an iOS end-to-end test triage assistant. A deterministic test \
scenario ran against an app on the iOS Simulator and a step or expectation failed. Explain \
the ROOT CAUSE of the failure and propose the minimal fix a human should apply.

You are advisory only — you diagnose and suggest. {NEVER_JUDGE_BOUNDARY} Reason strictly \
from the evidence given: the failure message, the failed step, the accessibility element tree \
captured nearest the failure, a screenshot of that screen when one is attached, and the \
scenario definition. Use the screenshot for visual state the element tree omits (what screen \
is actually shown, a blocking overlay, an empty/loading state). Never invent element ids.

Call the `diagnose` tool exactly once with:
- category, one of:
  - selector: the step's target id could not be resolved (absent from the screen, or it \
matched more than one element). If the target id is missing but a similar id IS on the \
captured screen, the id was likely renamed — say "did you mean <id>?".
  - timing: a wait/condition was not met before its timeout, or an assertion raced ahead of \
asynchronous UI — the element is reachable but not present yet.
  - assertion: the screen was reached but an expectation about its state did not hold.
  - unknown: the evidence does not support any of the above.
- summary: one or two sentences naming the concrete root cause.
- suggestions: concrete, minimal edits (a renamed id, `within` / `index` to disambiguate a \
selector, a longer timeout or an explicit wait, a corrected expected value). Prefer the \
smallest change that makes the scenario deterministic again.
- fix (an automatically-applicable edit; include ONLY when you are confident, else omit). \
`find` MUST be an exact substring of the scenario definition shown below, and `replace` is \
what it becomes:
  - renameId: a misspelled/renamed selector id whose correct id is visible on screen. \
find = the id the scenario uses now, replace = the correct id.
  - addIndex: an ambiguous selector that matched several elements. find = the exact selector \
fragment of the failing step (e.g. `{{ id: row.cell }}`), replace = the same fragment with \
`index:` (or `within:`) added to pick one.
  - raiseTimeout: a wait that timed out though the element was reachable. find = the exact \
`timeout: N` fragment of the failing wait, replace = it with a larger number.
Omit `fix` for assertion failures, or whenever you cannot name an exact `find` fragment."""

# Static tool definition (cached together with the system prompt). Its shape mirrors the
# `Triage` dataclass so the tool input maps straight back to it.
TOOLS: list[ToolDef] = [
    ToolDef(
        name="diagnose",
        description="Report the root-cause diagnosis of the failed scenario and the minimal fixes.",
        input_schema={
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "one or two sentences naming the concrete root cause",
                },
                "category": {"type": "string", "enum": list(_CATEGORIES)},
                "suggestions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "concrete, minimal fixes a human can apply",
                },
                "fix": {
                    "type": "object",
                    "description": "an automatically-applicable edit; `find` MUST be an exact "
                    "substring of the scenario definition shown",
                    "properties": {
                        "kind": {
                            "type": "string",
                            "enum": list(FIX_KINDS),
                            "description": "renameId (misspelled/renamed id), addIndex "
                            "(disambiguate an ambiguous match), raiseTimeout (lengthen a wait)",
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


class ClaudeTriageAgent(ClaudeBackedAgent):
    """TriageAgent implementation that asks Claude for the diagnosis via forced tool use."""

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

    def triage(self, context: TriageContext) -> Triage:
        # Force the one diagnose call; no thinking with forced choice.
        response = _forced_diagnose(
            self._ensure_backend(),
            _user_content(context, self._redactor),
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            model=self._model,
            max_tokens=self._max_tokens,
            ai=self._ai,
        )
        return _to_triage(response)
