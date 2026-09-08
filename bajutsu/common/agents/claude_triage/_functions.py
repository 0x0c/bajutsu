"""Lay out a failure's context for the model and read its tool call back into a verdict."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from bajutsu.common.agents.ai_config import AiConfig
from bajutsu.common.ai import (
    AiBackend,
    AnyTool,
    ContentPart,
    ImagePart,
    Message,
    MessageRequest,
    MessageResponse,
    TextPart,
    ToolDef,
    resolved_provider,
)
from bajutsu.common.ai.prompts import render_elements
from bajutsu.common.analytics import usage
from bajutsu.common.evidence.redaction import Redactor
from bajutsu.triage.heuristic import (
    FIX_KINDS,
    CrossRunTriageContext,
    Fix,
    RunEvidence,
    Triage,
    TriageContext,
    fix_summary,
)

_CATEGORIES = ("selector", "timing", "assertion", "unknown")

# The summary returned when the model produces no diagnose tool call. Named so tests can assert a
# real diagnosis differs from it without duplicating the literal (a copy would silently drift).
NO_DIAGNOSIS_SUMMARY = "Claude returned no diagnosis."


def _render(context: TriageContext, redactor: Redactor | None = None) -> str:
    """The user message: the failure context, laid out for the model to reason over.

    Every textual field that could carry a secret — the failure message, the failed step's action
    and reason, the failed expectations, the element tree, and the scenario YAML — is masked via
    `redactor` before it reaches the model (BE-0047). The screenshot (sent in `_user_content`)
    cannot be.
    """
    scrub = redactor.redact_text if redactor is not None else (lambda t: t)
    lines = [
        f"Scenario: {context.scenario}",
        f"Failure: {scrub(context.failure) or '(none reported)'}",
    ]
    if context.failed_step is not None:
        fs = context.failed_step
        # `action` comes from the manifest and can embed typed text (e.g. a password), so scrub it
        # too — not just `reason` (BE-0047).
        lines.append(f"Failed step: [{fs.index}] {scrub(fs.action)} — {scrub(fs.reason)}")
    if context.target_id:
        lines.append(f"Target id of the failed step: {context.target_id}")
    if context.failed_expectations:
        lines.append("Failed expectations:")
        lines += [f"  - {scrub(e)}" for e in context.failed_expectations]

    lines += ["", "Accessibility elements captured nearest the failure:"]
    elements = (
        redactor.redact_elements(context.elements) if redactor is not None else context.elements
    )
    # Key the fallback off `elements` itself, not the filtered result: a captured tree that renders
    # to nothing (app-root-only, a blank/loading screen) is a different root cause than a failed
    # capture, and a triage assistant must not conflate the two. When the tree is present but every
    # element is filtered out, say so explicitly rather than leave the section blank.
    if elements:
        body = render_elements(elements, compact=False)
        lines += body or [
            "(no addressable elements; only the app root or empty elements were captured)"
        ]
    else:
        lines.append("(no element tree captured)")

    if context.scenario_yaml:
        lines += ["", "Scenario definition (YAML):", scrub(context.scenario_yaml).rstrip()]
    if context.evidence:
        lines += ["", f"Evidence captured: {', '.join(context.evidence)}"]
    if context.screenshot is not None:
        lines += ["", "A screenshot of the screen at the failure is attached above."]
    lines += ["", "Call the `diagnose` tool exactly once."]
    return "\n".join(lines)


def _user_content(context: TriageContext, redactor: Redactor | None = None) -> list[ContentPart]:
    """The user message: the failure screenshot (if any) followed by the redacted text context."""
    content: list[ContentPart] = []
    if context.screenshot is not None:
        content.append(ImagePart(data=context.screenshot))
    content.append(TextPart(text=_render(context, redactor)))
    return content


def _parse_fix(raw: Any) -> Fix | None:
    """Accept a model-proposed fix only if it is a well-formed, non-trivial find/replace."""
    if not isinstance(raw, dict):
        return None
    kind, find, replace = raw.get("kind"), raw.get("find"), raw.get("replace")
    if kind not in FIX_KINDS or not isinstance(find, str) or not isinstance(replace, str):
        return None
    if not find or not replace or find == replace:
        return None
    return Fix(kind, fix_summary(kind, find, replace), find, replace)


def _to_triage(response: MessageResponse, categories: tuple[str, ...] = _CATEGORIES) -> Triage:
    tool_use = response.first_tool_use()
    if tool_use is None:
        return Triage(NO_DIAGNOSIS_SUMMARY, "unknown", [])
    args = tool_use.input
    category = str(args.get("category", "unknown"))
    if category not in categories:
        category = "unknown"
    suggestions = [str(s) for s in (args.get("suggestions") or [])]
    return Triage(
        str(args.get("summary", "")), category, suggestions, fix=_parse_fix(args.get("fix"))
    )


def _forced_diagnose(
    backend: AiBackend,
    content: list[ContentPart],
    *,
    system: str,
    tools: list[ToolDef],
    model: str,
    max_tokens: int,
    ai: AiConfig | None,
) -> MessageResponse:
    """Run one forced `diagnose` tool call and record its usage — shared by both triage agents."""
    response = backend.create_message(
        MessageRequest(
            system=system,
            messages=[Message(role="user", content=content)],
            tools=tools,
            tool_choice=AnyTool(),
            model=model,
            max_tokens=max_tokens,
        )
    )
    usage.record(response.usage, provider=resolved_provider(ai), model=model)
    return response


def _representative_screenshot_run(runs: Sequence[RunEvidence]) -> RunEvidence | None:
    """The one run per group whose screenshot is actually attached (the payload is bounded to one).

    `_render_evidence` and `_cross_run_user_content` both key off this, so the note a run carries and
    the image actually sent stay in lockstep.
    """
    return next((ev for ev in runs if ev.screenshot is not None), None)


def _render_evidence(
    ev: RunEvidence, label: str, scrub: Any, redactor: Redactor | None, *, screenshot_attached: bool
) -> list[str]:
    """One run's block in the cross-run message: its verdict plus the state nearest its end/failure."""
    lines = [f"{label} {ev.run_id} ({'passed' if ev.ok else 'failed'}):"]
    if ev.failure:
        lines.append(f"  Failure: {scrub(ev.failure)}")
    if ev.failed_step is not None:
        fs = ev.failed_step
        lines.append(f"  Failed step: [{fs.index}] {scrub(fs.action)} — {scrub(fs.reason)}")
    lines += [f"  Failed expectation: {scrub(e)}" for e in ev.failed_expectations]
    elements = redactor.redact_elements(ev.elements) if redactor is not None else ev.elements
    caption = "  Elements nearest the failure:" if not ev.ok else "  Elements at the run's end:"
    lines.append(caption)
    # Same distinction as `_render`: a captured-but-empty-after-filter tree is not a failed capture,
    # and a present-but-all-filtered tree still gets an explicit line rather than a blank section.
    if elements:
        body = render_elements(elements, compact=False)
        lines += [f"    {line}" for line in body] or ["    (no addressable elements)"]
    else:
        lines.append("    (no element tree captured)")
    if screenshot_attached:
        lines.append("  A screenshot of this run's screen is attached above.")
    return lines


def _render_cross_run(context: CrossRunTriageContext, redactor: Redactor | None = None) -> str:
    """The user message: the flaky scenario's passing and failing runs, laid out to contrast.

    Every textual field that could carry a secret is masked via `redactor` before it reaches the
    model (BE-0047), exactly as the single-run `_render` does; the screenshots (sent in
    `_cross_run_user_content`) cannot be.
    """
    scrub = redactor.redact_text if redactor is not None else (lambda t: t)
    lines = [f"Scenario: {context.scenario}"]
    if context.scenario_hash:
        lines.append(f"Content fingerprint (scenarioHash): {context.scenario_hash}")
    if context.target_id:
        lines.append(f"Target id of the flaky step: {context.target_id}")
    lines.append(
        "This scenario flips verdict at one fixed fingerprint. Contrast its failing and passing "
        "runs and explain what VARIES between them."
    )
    for group, label in ((context.failing, "Failing run"), (context.passing, "Passing run")):
        shot_run = _representative_screenshot_run(group)
        for ev in group:
            attached = ev is shot_run
            lines += [
                "",
                *_render_evidence(ev, label, scrub, redactor, screenshot_attached=attached),
            ]
    if context.scenario_yaml:
        lines += ["", "Scenario definition (YAML):", scrub(context.scenario_yaml).rstrip()]
    lines += ["", "Call the `diagnose` tool exactly once."]
    return "\n".join(lines)


def _cross_run_user_content(
    context: CrossRunTriageContext, redactor: Redactor | None = None
) -> list[ContentPart]:
    """The user message: the representative failing/passing screenshots then the redacted text.

    Attaches at most one failing and one passing screenshot (the first of each) to bound the payload
    — the text block already carries every run's element tree.
    """
    content: list[ContentPart] = []
    for runs in (context.failing, context.passing):
        shot_run = _representative_screenshot_run(runs)
        if shot_run is not None and shot_run.screenshot is not None:
            content.append(ImagePart(data=shot_run.screenshot))
    content.append(TextPart(text=_render_cross_run(context, redactor)))
    return content
