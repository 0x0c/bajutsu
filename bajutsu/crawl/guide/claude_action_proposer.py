"""The Claude-backed proposer: ask the model for candidates through a forced tool call."""

from __future__ import annotations

from bajutsu.common.agents.ai_config import AiConfig, language_instruction
from bajutsu.common.agents.claude_backed import ClaudeBackedAgent
from bajutsu.common.ai import AiBackend, Message, MessageRequest, NamedTool, ToolDef
from bajutsu.common.ai.prompts import NEVER_JUDGE_BOUNDARY
from bajutsu.common.analytics import usage
from bajutsu.common.drivers import base
from bajutsu.common.evidence.redaction import Redactor
from bajutsu.crawl import core as crawl

from ._functions import _content, _proposal_from, _secure_fields
from .proposal import Proposal

MODEL = "claude-opus-4-8"


# --- Claude-backed proposer ---------------------------------------------------------------

_SYSTEM = f"""You drive a breadth-first crawl of an iOS app to discover as many distinct screens \
as possible. You are given the current screen (a screenshot and its element list) and the \
operations a DETERMINISTIC inspector already found here. Reason about what is possible and \
propose the operations most likely to reveal a NEW screen or to unblock a disabled control whose \
enabling condition is not obvious.

Rules:
- Build on the inspector's operations: keep the useful ones, and **combine** them when a single \
operation isn't enough — e.g. a `fill` that enters several fields at once so a submit button \
validates, since a button can stay disabled until the whole form is valid.
- For a text field, supply a realistic value for what it asks (a valid email, a password meeting \
common rules, a plausible name/number) — this is how you enable a control the placeholder can't.
- Switch through a tab bar's tabs before drilling into a tab's own content.
- Add any operation the inspector skipped (e.g. an element with no id, addressed by `label`).
- Address each element by `id` when it has one (most stable), else by `label` (+ `index`).
- If an OS prompt was just dismissed to reach this screen (noted below), take it into account — \
the app asked for something (a permission, to save a password); pick what makes sense next.
- You only choose what to TRY. {NEVER_JUDGE_BOUNDARY}"""

_PROPOSE_TOOL: ToolDef = ToolDef(
    name="propose_actions",
    description="Propose the operations to try from this screen, most promising first.",
    input_schema={
        "type": "object",
        "properties": {
            "thought": {
                "type": "string",
                "description": "one short sentence: what this screen is and why you'll try these "
                "operations (shown live to the watcher)",
            },
            "actions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["tap", "type", "fill"]},
                        "id": {
                            "type": "string",
                            "description": "accessibility identifier (preferred)",
                        },
                        "label": {
                            "type": "string",
                            "description": "exact label when there is no id",
                        },
                        "index": {"type": "integer", "description": "0-based pick among matches"},
                        "value": {
                            "type": "string",
                            "description": "text to enter (for a type action)",
                        },
                        "fields": {
                            "type": "array",
                            "description": "for a `fill`: every field to enter at once, with a "
                            "realistic value — use this when a control activates only after several "
                            "fields are valid (e.g. email + password)",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "value": {"type": "string"},
                                },
                                "required": ["id", "value"],
                            },
                        },
                    },
                    "required": ["action"],
                },
            },
        },
        "required": ["thought", "actions"],
    },
)


class ClaudeActionProposer(ClaudeBackedAgent):
    """Asks Claude for the screen's candidate operations via a forced tool call.

    Talks to the model through the vendor-neutral backend (BE-0104).
    """

    def __init__(
        self,
        backend: AiBackend | None = None,
        model: str | None = None,
        max_tokens: int = 1024,
        max_actions: int = 8,
        *,
        ai: AiConfig | None = None,
        redactor: Redactor | None = None,
    ) -> None:
        super().__init__(
            backend=backend, ai=ai, default_model=MODEL, model=model, redactor=redactor
        )
        self._lang = language_instruction(ai)  # output-language suffix, empty for `auto` (BE-0188)
        self._max_tokens = max_tokens
        self._max_actions = max_actions

    def propose(
        self,
        elements: list[base.Element],
        screenshot: bytes | None,
        candidates: list[crawl.Action],
        dismissed: tuple[str, ...],
    ) -> Proposal:
        secure = _secure_fields(elements)
        if self._redactor is not None:
            elements = self._redactor.redact_elements(elements)
        content = _content(elements, screenshot, candidates, dismissed, self._redactor)
        response = self._ensure_backend().create_message(
            MessageRequest(
                system=_SYSTEM + self._lang,
                messages=[Message(role="user", content=content)],
                tools=[_PROPOSE_TOOL],
                tool_choice=NamedTool(name="propose_actions"),
                model=self._model,
                max_tokens=self._max_tokens,
            )
        )
        # reporting only (BE-0104) — never on the pass/fail path
        self._record_usage(response)
        block = response.first_tool_use()
        if block is None:
            return Proposal()
        proposal = _proposal_from(block.input, self._max_actions, secure)
        proposal.tokens = usage.of(response.usage).total_tokens
        return proposal
