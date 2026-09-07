"""Render the agent's prompt and read the model's tool call back into a proposal."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast, get_args

from bajutsu.common.agents.protocols import HumanValueClass, Observation, Proposal
from bajutsu.common.ai import ContentPart, ImagePart, MessageResponse, TextPart, ToolUseBlock
from bajutsu.common.ai.prompts import render_elements
from bajutsu.common.evidence.redaction import Redactor
from bajutsu.common.scenario import Assertion, Selector, Step

from ._tool_args import _ToolArgs

if TYPE_CHECKING:
    from ._assertion_args import _AssertionArgs
    from ._target_args import _TargetArgs

# Above this many on-screen elements a turn is considered pathological (a long list / data table),
# and the non-addressable remainder is reported as a count rather than silently dropped (BE-0194 §2).
# A global constant, not per-app config (prime directive 3). Addressable elements are never dropped.
_LARGE_SCREEN_ELEMENTS = 50


def _hist_hint(sel: Selector | None) -> str:
    """The id or label to name a selector by in a recent-actions line (`?` when it has neither).

    `sel` may be None (a `type` / `wait` step whose target is unset): the `getattr` defaults then
    fall through to `?`, so a missing target reads the same as one with neither id nor label.
    """
    return next((str(v) for v in (getattr(sel, "id", None), getattr(sel, "label", None)) if v), "?")


def _history_line(step: Step) -> str:
    """A compact summary of an already-taken step, shown back to the agent to curb repetition.

    Secrets are never echoed — typed text is omitted.
    """
    if step.tap is not None:
        return f"tap {_hist_hint(step.tap)}"
    if step.tap_point is not None:
        return f"tap point ({step.tap_point.x:.2f}, {step.tap_point.y:.2f})"
    if step.swipe is not None and step.swipe.on is not None:
        return f"swipe {step.swipe.direction} on {_hist_hint(step.swipe.on)}"
    if step.type is not None:
        return f"type into {_hist_hint(step.type.into)}"
    if step.wait is not None:
        return f"wait for {_hist_hint(step.wait.for_)}"
    return next(iter(step.model_dump(exclude_none=True)), "step")


def _render(observation: Observation, redactor: Redactor | None = None) -> str:
    lines = [f"Goal: {observation.goal}"]
    if observation.plan:
        lines.append("")
        lines.append(
            "Planned steps (your up-front decomposition of the goal — follow it in order, "
            "adapting to what the screen actually shows):"
        )
        lines += [f"  {i}. {step}" for i, step in enumerate(observation.plan, 1)]
    lines += ["", "Current screen elements:"]
    # Mask secrets in the element tree before it reaches the model (BE-0047): a configured label /
    # field value or a literal secret echoed into label/value is replaced with [REDACTED].
    screen = (
        redactor.redact_elements(observation.screen) if redactor is not None else observation.screen
    )
    # Compact the lines (BE-0194 §1): render_elements emits only the addressing fields that carry
    # information, skipping the app root and any element with nothing to address it by.
    body = render_elements(screen, compact=True)
    shown = len(body)
    # The non-app remainder that render_elements dropped for carrying no addressing field (BE-0194
    # §2) — reported as a count only past the cap, so an addressable element is never silently lost.
    omitted = sum(1 for e in screen if "application" not in (e.get("traits") or [])) - shown
    lines += body
    if not shown:
        lines.append("- (no addressable elements; the screen may still be loading)")
    elif omitted and len(screen) > _LARGE_SCREEN_ELEMENTS:
        # A pathological screen (BE-0194 §2): every addressable element above is kept, and the
        # non-addressable remainder is collapsed into a reported count rather than silently dropped,
        # so the agent knows the screen was truncated (it can swipe to reveal more).
        lines.append(f"- (+{omitted} further non-addressable elements omitted)")
    lines += ["", f"Steps taken so far: {len(observation.history)}"]
    if observation.history:
        # Show the recent actions so the agent can see whether it is looping (repeating an action or
        # cycling between screens) and change course — the single biggest cause of a stuck record.
        recent = observation.history[-6:]
        lines.append("Recent actions (most recent last) — do not repeat these fruitlessly:")
        lines += [f"  - {_history_line(s)}" for s in recent]
    if observation.screenshot is None and observation.vision_available:
        # Vision-on-demand (BE-0192): this turn carries no image, but the session can supply one on
        # request. Say so, and remind the agent it can pull the screen back with need_screenshot when
        # the elements above genuinely do not suffice.
        lines.append(
            "No screenshot this turn — the elements above are authoritative for addressing. Call "
            "need_screenshot only if you genuinely must see the screen to proceed (a control you "
            "need is not listed, or you must read an appearance the elements do not expose)."
        )
    elif observation.screenshot is None:
        # Screenshots are off for the whole session (`--no-screenshot`), so need_screenshot can never
        # be satisfied — telling the agent to escalate would dead-end the record. Direct it to act
        # from the elements alone and explicitly not to escalate (BE-0192).
        lines.append(
            "No screenshots are available this session — act from the elements above alone. Do NOT "
            "call need_screenshot; it cannot be satisfied here."
        )
    lines.append(
        "Call tap, tap_point, swipe, type_text, wait_for, or finish — one tool, or several "
        "action tools together only when all are determinable from THIS screen (see the rules)."
    )
    return "\n".join(lines)


def _target(args: _TargetArgs) -> dict[str, Any]:
    """A selector dict addressing one element: id when given, else label/value/traits (ANDed), index as last resort."""
    if args.get("id"):
        sel: dict[str, Any] = {"id": args["id"]}
        if args.get("index") is not None:
            sel["index"] = args["index"]
        return sel
    sel = {}
    if args.get("label") is not None:
        sel["label"] = args["label"]
    if args.get("value") is not None:
        sel["value"] = args["value"]
    if args.get("traits"):
        sel["traits"] = args["traits"]
    if not sel:
        raise ValueError("target needs an id, label, value, or traits")
    if args.get("index") is not None:
        sel["index"] = args["index"]
    return sel


def _has_target(args: _TargetArgs) -> bool:
    """Whether `args` addresses an element at all — `ask_human` may name no field (BE-0182)."""
    return bool(
        args.get("id")
        or args.get("label") is not None
        or args.get("value") is not None
        or args.get("traits")
    )


def _provenance(value: str | None) -> dict[str, str]:
    """`{"from": value}` when there is a phrase to record, else `{}` so empty provenance is omitted (BE-0044)."""
    return {"from": value} if value else {}


def _to_assertion(item: _AssertionArgs) -> Assertion:
    sel = _target(item)
    check = item.get("check")
    if check is None:
        raise ValueError(f"assertion missing required 'check' field: {dict(item)!r}")
    text = item.get("text")
    # The natural-language phrase this check verifies (BE-0044 provenance) — optional.
    prov = _provenance(item.get("intent"))
    if check == "exists":
        return Assertion.model_validate({"exists": sel, **prov})
    if check == "notExists":
        return Assertion.model_validate({"exists": {**sel, "negate": True}, **prov})
    if check == "valueEquals":
        return Assertion.model_validate({"value": {"sel": sel, "equals": text}, **prov})
    if check == "labelContains":
        return Assertion.model_validate({"label": {"sel": sel, "contains": text}, **prov})
    raise ValueError(f"unknown assertion check: {check!r}")


def proposal_from_call(name: str, args: _ToolArgs) -> Proposal:
    """Turn one tool/action call — `(name, args)` — into a Proposal.

    Shared by the API agent (a Claude tool_use block) and the Claude Code agent (a
    structured-output object), so both backends map the same action shape to the same
    scenario step.

    The tool's `reason` (why this action advances the goal) is the natural-language intent behind
    the action, so it is recorded as the step's `from:` provenance (BE-0044) as well as the note.
    """
    note = args.get("reason", "")
    prov = _provenance(note)
    raw_ps = args.get("plan_step")
    ps = raw_ps if isinstance(raw_ps, int) and not isinstance(raw_ps, bool) else None
    if name == "tap":
        step = {"tap": _target(args), **prov}
        return Proposal(steps=[Step.model_validate(step)], note=note, plan_step=ps)
    if name == "tap_point":
        point = {"tapPoint": {"x": args["x"], "y": args["y"]}, **prov}
        return Proposal(steps=[Step.model_validate(point)], note=note, plan_step=ps)
    if name == "swipe":
        spec: dict[str, Any] = {"on": _target(args), "direction": args["direction"]}
        if args.get("amount") is not None:
            spec["amount"] = args["amount"]
        return Proposal(
            steps=[Step.model_validate({"swipe": spec, **prov})], note=note, plan_step=ps
        )
    if name == "type_text":
        step = {"type": {"into": _target(args), "text": args["text"]}, **prov}
        return Proposal(steps=[Step.model_validate(step)], note=note, plan_step=ps)
    if name == "wait_for":
        step = {"wait": {"for": _target(args), "timeout": args["timeout"]}, **prov}
        return Proposal(steps=[Step.model_validate(step)], note=note, plan_step=ps)
    if name == "finish":
        expect = [_to_assertion(a) for a in args.get("assertions", [])]
        return Proposal(done=True, expect=expect, note=note, plan_step=ps)
    if name == "ask_human":
        # A "needs human" turn (BE-0179): the loop hands off to a human and resumes by re-observing.
        # When the agent also addresses the field the value goes into (BE-0182), carry the target
        # selector, its proposed classification, and a placeholder name so the loop can type the
        # value live and record a deterministic ${vars.*} / ${secrets.*} placeholder step. A handoff
        # that names no field (a CAPTCHA, a takeover) stays a bare re-observe.
        field = Selector.model_validate(_target(args)) if _has_target(args) else None
        raw_classify = args.get("classify")
        classify: HumanValueClass | None = (
            cast(HumanValueClass, raw_classify)
            if raw_classify in get_args(HumanValueClass)
            else None
        )
        return Proposal(
            needs_human=True,
            human_prompt=args.get("prompt") or note,
            human_field=field,
            human_classify=classify,
            human_var=args.get("name") or None,
            human_bypass=args.get("bypass") or None,
            note=note,
            plan_step=ps,
        )
    if name == "need_screenshot":
        # An escalation (BE-0192): on a text-only turn the agent asks to see the screen. The loop
        # re-issues the same observation once with a screenshot attached — no step, not done.
        return Proposal(need_screenshot=True, note=note, plan_step=ps)
    raise ValueError(f"unknown tool: {name!r}")


def steps_from_plan(raw: object) -> list[str]:
    """Normalize a `plan` tool/structured-output result into a clean list of step strings.

    Shared by both backends so the API agent and the Claude Code agent return the same shape.
    """
    if not isinstance(raw, (list, tuple)):
        return []
    return [str(step).strip() for step in raw if str(step).strip()]


def _combine(subs: list[Proposal]) -> Proposal:
    """Fold the per-action proposals of one turn into a single batch proposal (BE-0178).

    Actions are collected in order; a `finish` terminates the batch (Decision 3) — the actions
    before it stay in `steps`, and its assertions become the batch's `expect`. A `needs_human`
    (BE-0179) likewise terminates the batch, carrying its `human_prompt` so the loop can hand off.
    Turn-level `note` and `plan_step` are taken from the first action (each step also carries its
    own `from_` reason).
    """
    steps: list[Step] = []
    note, plan_step = subs[0].note, subs[0].plan_step
    for sub in subs:
        if sub.need_screenshot:
            # An escalation (BE-0192) discards the turn's actions: the agent wants to see the screen
            # before committing to any action, so nothing is executed this turn — the loop re-issues
            # with the image and the agent re-decides. Returning `steps=[]` (not the accumulated
            # steps) makes that honest, so a stray `[tap, need_screenshot]` batch never executes the
            # tap on a turn the escalation cannot re-issue (e.g. a screenshot was already attached).
            return Proposal(steps=[], need_screenshot=True, note=note, plan_step=plan_step)
        if sub.needs_human:
            # Forward the value-handoff details (BE-0182) and the takeover bypass (BE-0185) too —
            # without them the record loop can never reach the value / takeover branch on the live
            # path (every real turn goes through _combine).
            return Proposal(
                steps=steps,
                needs_human=True,
                human_prompt=sub.human_prompt,
                human_field=sub.human_field,
                human_classify=sub.human_classify,
                human_var=sub.human_var,
                human_bypass=sub.human_bypass,
                note=note,
                plan_step=plan_step,
            )
        if sub.done:
            return Proposal(
                steps=steps, done=True, expect=sub.expect, note=note, plan_step=plan_step
            )
        steps.extend(sub.steps)
    return Proposal(steps=steps, note=note, plan_step=plan_step)


def _to_proposal(response: MessageResponse) -> Proposal:
    # Map every tool-use block in the turn to a step, in order (BE-0178) — the agent may emit
    # several actions determinable from the current screen. A turn with no tool call is done.
    # A ToolUseBlock's `input` is the SDK's raw JSON object (`dict[str, Any]`); the model was forced
    # to one of our tools, so it matches `_ToolArgs` — narrow it here at that one boundary.
    subs = [
        proposal_from_call(b.name, cast(_ToolArgs, b.input))
        for b in response.content
        if isinstance(b, ToolUseBlock)
    ]
    if not subs:
        return Proposal(done=True, note="model returned no tool call")
    return _combine(subs)


def _user_content(observation: Observation, redactor: Redactor | None = None) -> list[ContentPart]:
    """The per-turn user message: the screenshot (if any) followed by the redacted text.

    The screenshot is sent as-is — images cannot be pixel-masked; the textual element tree is
    redacted via `redactor` (BE-0047). Both reach only the user-configured provider/endpoint.
    """
    content: list[ContentPart] = []
    if observation.screenshot is not None:
        content.append(ImagePart(data=observation.screenshot))
    content.append(TextPart(text=_render(observation, redactor)))
    return content
