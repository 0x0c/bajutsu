"""The authoring agent backed by Claude: ask the model for the next action through tool use."""

from __future__ import annotations

from typing import get_args

from bajutsu.common.agents.ai_config import AiConfig, language_instruction, resolve_effort
from bajutsu.common.agents.claude_backed import ClaudeBackedAgent
from bajutsu.common.agents.protocols import HumanValueClass, Observation, Proposal
from bajutsu.common.ai import (
    AiBackend,
    AnyTool,
    Message,
    MessageRequest,
    NamedTool,
    TextPart,
    ToolDef,
)
from bajutsu.common.analytics import usage
from bajutsu.common.evidence.redaction import Redactor

from ._functions import _to_proposal, _user_content, steps_from_plan
from ._shared import _PLAN_PROP, _REASON_PROP, _TARGET_PROPS

MODEL = "claude-opus-4-8"

# Wall-clock cap for the best-effort up-front plan call — well above its normal few seconds, but
# short enough that an occasional CLI hang fails fast and the loop proceeds without a plan.
PLAN_TIMEOUT_S = 60.0

SYSTEM_PROMPT = """You are an iOS end-to-end test author. You drive an app on the \
iOS Simulator to accomplish a goal, then record the steps as a deterministic test.

Each turn you receive the goal and the screen's accessibility elements. A screenshot \
of the current screen MAY also be present, but not every turn: it is attached the first \
time a screen is seen and whenever the elements are too sparse to act on, and omitted on \
a screen you have already seen whose elements fully determine the action. The element \
list is ALWAYS authoritative for addressing. Each element has a `label`, `value`, and \
`traits`, and — only if the app instrumented it — a stable `id`. Address an element by:

- `id` when it has one — non-localized and data-derived, so ALWAYS prefer it; otherwise
- any combination of `label` (exact accessibility label), `value` (exact value — e.g. \
an empty text field exposes its placeholder like "Email" as its value), and `traits` \
(e.g. ["textField"], ["button"]). These are ANDed, so combine them to pin one element \
(a text field with value "Email" → value="Email", traits=["textField"]).
- add `index` (0-based, in the listed order) only when several elements still match.

When a screenshot is present, use it to map the goal's wording to the right element when \
the text differs from it (e.g. a "+" button is the increment control). Call one of these tools:

- tap(id|label): tap that element.
- tap_point(x, y): tap a screen location by NORMALIZED coordinates (0..1 from the \
top-left corner), read from the screenshot. Use this for a control you can SEE in the \
screenshot but that is NOT in the element list — a tab-bar tab, a segmented-control \
segment, a toolbar item, on an app whose accessibility tree omits it. Aim at the CENTER \
of the control's visible hit area. For a tab-bar tab, that is the center of the rectangle \
enclosing BOTH its icon and its label — not the icon alone, and not the empty strip below \
the label. Horizontally, the i-th of N equal-width tabs sits at x ≈ (i − 0.5)/N (the 3rd \
of 5 tabs → x ≈ 0.5); vertically, aim midway through the icon and label, typically \
y ≈ 0.94 in a bottom tab bar.
- swipe(id|label, direction): swipe on a visible element (up/down/left/right) to SCROLL \
a list or form. Use it to bring a control that is off-screen — neither in the element \
list nor visible in the screenshot — into view before acting on it. Set `amount` (a \
fraction of the screen, 0–1) to control how far it scrolls: a small nudge by default, or \
0.5–0.9 to move quickly toward a control you expect to be far down. Increase it if a \
previous swipe barely moved the screen.
- type_text(id|label, text): focus the field and type text into it.
- wait_for(id|label, timeout): wait until that element appears.
- finish(assertions): the goal is reached; provide machine-checkable assertions \
that verify it, each addressing an element by id or label.
- need_screenshot(): ask to see the current screen. Use ONLY on a turn that arrived \
without a screenshot, and only when you genuinely cannot proceed from the element list \
alone — a control you need is not listed, or you must read an appearance the elements do \
not expose. The same, unchanged screen is re-shown once with a screenshot attached; do \
not call it when the elements already determine your action.
- ask_human(prompt): hand off to a human when the next step needs a value you cannot \
possibly know in a real run (a one-time password, a verification / 2FA code, a CAPTCHA) \
or an action only a human can perform. The person authoring supplies it and the recording \
resumes — you never guess. When the value goes into a specific field, ALSO address that \
field (id/label/value/traits) and propose how a real run supplies it with classify (totp/email/secret) \
and a short name — the recording keeps only a ${vars.*}/${secrets.*} placeholder, never the \
literal value. For an action only a human can perform, if a deterministic bridge exists \
(a test-build flag, or a device-control / device-state primitive), name it via bypass so a \
real run can wire that instead of the human.

Rules:
- Usually call ONE tool. You MAY call several action tools in one turn ONLY when each is \
determinable from the CURRENT screen without seeing the previous action's effect — e.g. fill \
several form fields, then tap Submit; the actions run in the order you give them. Do NOT batch \
when a later action depends on what an earlier one reveals (a field that only appears after a \
tap, a screen you must first navigate to): emit one action and see the next screen. If the \
screen changes partway through a batch, the remaining actions are dropped and you re-observe — \
so batching is safe, but only helps when the whole batch really is determinable up front.
- Act only on elements present in the screen list; address them by their real `id` \
or `label`. Never invent an id or a label that is not shown.
- For a control missing from the list, choose by WHERE it is: if you can see it in the \
screenshot, tap_point its center; if you cannot see it, it is off-screen — swipe to \
scroll it into view first. Never use tap_point for an element that IS listed — address \
that one by id/label, which is far more stable. Prefer these over giving up on the goal.
- NEVER type a one-time password, a verification code, or a 2FA code — even when one is \
shown on the screen. In a real run it arrives out-of-band and you cannot know it, so reading \
a test fixture's code would bake a stale value into the recording. Call ask_human for it.
- Take the most direct path to the goal. NEVER repeat an action that did not move you \
toward the goal, and never re-open a screen you just closed. If a step left you where you \
were, or you are cycling between two screens, change your approach: scroll to look \
elsewhere, or tap_point a control you can see. The recent steps you have taken are listed \
each turn — read them and do not loop.
- Always fill `reason`: one short sentence of your reasoning for THIS turn — what you \
see on the screen and why this action moves toward the goal. This is shown live to the \
person watching, so make it a clear thought, not a restatement of the action.
- When a plan is shown this turn, set `plan_step` to the number of the planned step this \
action carries out, so the watcher sees where the run is in the plan. Omit it if there is no plan.
- Call finish only once the goal is FULLY reached. If the goal names a target \
value or count (e.g. "the count shows 2"), confirm the current screen already \
shows it before finishing; if not, keep acting. Then provide assertions that \
prove it — prefer `valueEquals` against an element's `value`, or `labelContains` \
when the number is part of the label (e.g. a "Count: 2" text)."""

PLAN_SYSTEM = """You are an iOS end-to-end test author. Before driving the app, break the \
user's goal into a short, ordered list of concrete, human-readable steps — the procedure a \
tester would follow on screen to accomplish it.

Each step is ONE plain-language action or check, in the order it happens, e.g.:
- "Tap the 'Get Started' button on the welcome screen"
- "Enter an email address into the Email field"
- "Tap 'Add to Cart' on the product"
- "Confirm the cart badge shows 2 items"

Guidance:
- Keep it concrete and minimal — 2–8 steps is typical. End with the check that confirms the goal.
- You have NOT seen the screen yet, so describe intent, not specific element ids; do not invent ids.
- This plan is shown to the person watching and guides the run, but the live screen is the source \
of truth — it is fine if the actual run deviates.

Call the `plan` tool exactly once."""

PLAN_TOOL: ToolDef = ToolDef(
    name="plan",
    description="Record the ordered, concrete steps to accomplish the goal.",
    input_schema={
        "type": "object",
        "properties": {
            "steps": {
                "type": "array",
                "items": {"type": "string"},
                "description": "ordered concrete steps, each a short plain-language action or check",
            }
        },
        "required": ["steps"],
    },
)

# Static tool definitions (cached together with the system prompt).
TOOLS: list[ToolDef] = [
    ToolDef(
        name="tap",
        description="Tap the element addressed by id or label.",
        input_schema={
            "type": "object",
            "properties": {**_TARGET_PROPS, **_REASON_PROP, **_PLAN_PROP},
            "required": ["reason"],
        },
    ),
    ToolDef(
        name="tap_point",
        description="Tap a screen location by normalized coordinates (0..1) read from the "
        "screenshot — only for a visible control absent from the element list, e.g. a tab-bar tab.",
        input_schema={
            "type": "object",
            "properties": {
                "x": {
                    "type": "number",
                    "description": "horizontal center, a fraction of screen width (0 = left, 1 = right)",
                },
                "y": {
                    "type": "number",
                    "description": "vertical center, a fraction of screen height (0 = top, 1 = bottom)",
                },
                **_REASON_PROP,
                **_PLAN_PROP,
            },
            "required": ["x", "y", "reason"],
        },
    ),
    ToolDef(
        name="swipe",
        description="Swipe on a visible element in a direction to scroll a list/form and reveal an "
        "off-screen control (one neither in the element list nor visible in the screenshot).",
        input_schema={
            "type": "object",
            "properties": {
                **_TARGET_PROPS,
                "direction": {"type": "string", "enum": ["up", "down", "left", "right"]},
                "amount": {
                    "type": "number",
                    "description": "how far to scroll as a fraction of the screen (0-1): ~0.2 a "
                    "little, ~0.5 half a screen, ~0.9 nearly a full screen. Judge it from how far "
                    "the target likely is; omit for a small default nudge.",
                },
                **_REASON_PROP,
                **_PLAN_PROP,
            },
            "required": ["direction", "reason"],
        },
    ),
    ToolDef(
        name="type_text",
        description="Focus the field (addressed by id or label) and type the given text.",
        input_schema={
            "type": "object",
            "properties": {
                **_TARGET_PROPS,
                "text": {"type": "string"},
                **_REASON_PROP,
                **_PLAN_PROP,
            },
            "required": ["text", "reason"],
        },
    ),
    ToolDef(
        name="wait_for",
        description="Wait until the element (addressed by id or label) appears, up to timeout seconds.",
        input_schema={
            "type": "object",
            "properties": {
                **_TARGET_PROPS,
                "timeout": {"type": "number"},
                **_REASON_PROP,
                **_PLAN_PROP,
            },
            "required": ["timeout", "reason"],
        },
    ),
    ToolDef(
        name="finish",
        description="The goal is reached; provide the assertions that verify it.",
        input_schema={
            "type": "object",
            "properties": {
                "assertions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            **_TARGET_PROPS,
                            "check": {
                                "type": "string",
                                "enum": ["exists", "notExists", "valueEquals", "labelContains"],
                            },
                            "text": {
                                "type": "string",
                                "description": "expected text for valueEquals / labelContains",
                            },
                            "intent": {
                                "type": "string",
                                "description": "the natural-language phrase this check verifies "
                                "(recorded as the assertion's `from:` provenance)",
                            },
                        },
                        "required": ["check"],
                    },
                },
                **_REASON_PROP,
                **_PLAN_PROP,
            },
            "required": ["assertions", "reason"],
        },
    ),
    ToolDef(
        name="need_screenshot",
        description="Ask to see the current screen. Call this ONLY on a turn that arrived without a "
        "screenshot, and only when you genuinely cannot proceed from the element list alone — a "
        "control you need is not listed, or you must read an appearance the elements do not expose. "
        "The same, unchanged screen is then re-shown to you once with a screenshot attached.",
        input_schema={
            "type": "object",
            "properties": {**_REASON_PROP, **_PLAN_PROP},
            "required": ["reason"],
        },
    ),
    ToolDef(
        name="ask_human",
        description="Hand off to a human: the next step needs a value you cannot possibly know in a "
        "real run (a one-time password, a verification / 2FA code, a CAPTCHA answer) or an action "
        "only a human can perform. Never guess or read such a value off the screen. When the value "
        "goes into a specific field, ALSO address that field (id / label / value / traits) and "
        "propose how a real run will supply it via `classify`: 'totp' (a code from an authenticator "
        "seed), 'email' (a code delivered to an inbox), or 'secret' (a fixed secret you declare). "
        "The human types the value once now; the recording keeps only a placeholder, never the "
        "literal — so name it with `name` (e.g. 'otp_code'). When the operation has no field to "
        "fill but a deterministic bridge could stand in for it (a test-build flag, or a "
        "device-control / device-state primitive), ALSO name that bridge via `bypass`.",
        input_schema={
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "what the human must supply or do, in one short sentence "
                    "(e.g. 'enter the one-time verification code shown on the device')",
                },
                **_TARGET_PROPS,
                "classify": {
                    "type": "string",
                    "enum": list(get_args(HumanValueClass)),
                    "description": "how a real run should supply this value deterministically — "
                    "'totp'/'email' produce a ${vars.*} via a run-time step (BE-0046), 'secret' a "
                    "declared ${secrets.*}. A proposal only; the author confirms and wires it.",
                },
                "name": {
                    "type": "string",
                    "description": "a short placeholder name for the value (e.g. 'otp_code'), used "
                    "for the recorded ${vars.*} / ${secrets.*} token; omit to derive one",
                },
                "bypass": {
                    "type": "string",
                    "description": "for an operation only a human can perform (a CAPTCHA, a biometric "
                    "prompt) with no field to fill: a deterministic bypass a real run could wire — a "
                    "test-build flag, or a device-control / device-state primitive (BE-0035 / "
                    "BE-0052). Recorded as a TODO on the manual marker; omit when none exists (a real "
                    "CAPTCHA), leaving an honest step that fails loudly at run time.",
                },
                **_REASON_PROP,
                **_PLAN_PROP,
            },
            "required": ["prompt", "reason"],
        },
    ),
]


class ClaudeAgent(ClaudeBackedAgent):
    """Agent implementation that asks Claude for the next action via tool use."""

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
        self._effort = resolve_effort(ai)  # passed to backends that support it (claude-code)
        # Output-language suffix (BE-0188), empty for `auto`. Folded onto the static system prompts
        # below so the reasoning/plan prose comes out in the chosen language.
        self._lang = language_instruction(ai)
        self._max_tokens = max_tokens

    def next_action(self, observation: Observation) -> Proposal:
        # Force one tool call; no thinking with forced choice.
        response = self._ensure_backend().create_message(
            MessageRequest(
                system=SYSTEM_PROMPT + self._lang,
                messages=[Message(role="user", content=_user_content(observation, self._redactor))],
                tools=TOOLS,
                tool_choice=AnyTool(),
                model=self._model,
                max_tokens=self._max_tokens,
                effort=self._effort,
            )
        )
        self._record_usage(response, usage.CATEGORY_ACTION)
        return _to_proposal(response)

    def plan(self, goal: str) -> list[str]:
        response = self._ensure_backend().create_message(
            MessageRequest(
                system=PLAN_SYSTEM + self._lang,
                messages=[Message(role="user", content=[TextPart(text=f"Goal: {goal}")])],
                tools=[PLAN_TOOL],
                tool_choice=NamedTool(name="plan"),  # force the plan call
                model=self._model,
                max_tokens=self._max_tokens,
                effort=self._effort,
                # The plan is best-effort (the loop proceeds without it), so bound it: a hung CLI
                # fails fast here instead of stalling the run at "thinking about how to approach…".
                timeout_s=PLAN_TIMEOUT_S,
            )
        )
        self._record_usage(response, usage.CATEGORY_PLAN)
        block = response.first_tool_use()
        if block is None:
            return []
        return steps_from_plan(block.input.get("steps"))
