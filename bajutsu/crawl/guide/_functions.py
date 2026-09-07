"""Adapt a proposer to the crawl's guide seam, running the BE-0038 pipeline around it."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from bajutsu.common.agents.ai_config import AiConfig
from bajutsu.common.ai import ContentPart, ImagePart, TextPart
from bajutsu.common.ai.prompts import render_elements
from bajutsu.common.drivers import base
from bajutsu.common.evidence.redaction import Redactor
from bajutsu.common.screenshots import screenshot_bytes
from bajutsu.crawl import core as crawl
from bajutsu.crawl import tabs as crawl_tabs

from ._secure_fields import _SecureFields
from .action_proposer import ActionProposer
from .proposal import Proposal

# Receives the AI's reasoning as it explores, so a watcher (the crawl log / the web UI) can see
# what the model is thinking and which operations it chose.
Report = Callable[[str], None]


def ai_guide(
    proposer: ActionProposer,
    report: Report | None = None,
    tab_locator: crawl_tabs.TabLocator | None = None,
) -> crawl.Guide:
    """Adapt an `ActionProposer` to the crawl `Guide` signature, running the BE-0038 pipeline.

    First **inspect deterministically** (`candidate_actions`), then hand those operations + the
    screen (and any OS prompt just dismissed to reach it) to the proposer so it can reason about
    what's possible and **combine** them (realistic inputs, multi-field fills, id-less elements);
    finally union the proposal with the deterministic baseline (proposer first, so its values win
    on de-dup), narrating its reasoning via `report`.

    When `tab_locator` is set and a tab bar is present whose individual tabs the tree can't address
    (iOS surfaces a SwiftUI TabView as one "Tab Bar" group with no per-tab ids), it locates the
    tabs by vision — the same fallback the alert guard uses — and prepends a coordinate tap per tab,
    so the crawl still switches tabs first.
    """

    def guide(
        driver: base.Driver, elements: list[base.Element], context: crawl.GuideContext
    ) -> list[crawl.Action]:
        if report is not None:
            report("📸 capturing the current screen…")
        shot = screenshot_bytes(driver)
        candidates = crawl.candidate_actions(elements)  # deterministic inspection, fed to the AI
        tabs = _locate_tabs(tab_locator, elements, shot, report)
        if report is not None and context.dismissed:
            report(f"🛡️  factoring in a just-dismissed OS prompt: {', '.join(context.dismissed)}")
        if report is not None:
            report("🤖 asking Claude to choose the next operations (this waits on the model)…")
        proposal = proposer.propose(elements, shot, candidates, context.dismissed)
        if report is not None:
            spent = f" · {proposal.tokens:,} tokens" if proposal.tokens else ""
            report(f"🤖 Claude proposed {len(proposal.actions)} operation(s){spent}")
            if proposal.thought:
                report(f"🤔 {proposal.thought}")
            for a in proposal.actions:
                report(f"   → try {a.describe()}")
        # Tabs first (switch the whole view before drilling in), then the proposal, then the
        # deterministic baseline; de-dup keeps the earliest, so a vision tab beats a later duplicate.
        return _dedup([*tabs, *proposal.actions, *candidates])

    return guide


def _locate_tabs(
    tab_locator: crawl_tabs.TabLocator | None,
    elements: list[base.Element],
    shot: bytes | None,
    report: Report | None,
) -> list[crawl.Action]:
    """Vision fallback for an un-addressable tab bar: a coordinate tap per tab, only when a locator and screenshot exist and such a tab bar is present."""
    if tab_locator is None or shot is None or not crawl_tabs.needs_vision_tabs(elements):
        return []
    if report is not None:
        report("👁️  tab bar not addressable in the tree — asking Claude to locate tabs by vision…")
    targets = tab_locator.locate(shot)
    actions = [crawl.Action("tap_point", label=t.label, point=(t.x, t.y)) for t in targets]
    if report is not None and actions:
        named = ", ".join(t.label or f"({t.x:.2f},{t.y:.2f})" for t in targets)
        report(
            f"👁️  tab bar not addressable in the tree — vision found {len(actions)} tab(s): {named}"
        )
    return actions


def _dedup(actions: list[crawl.Action]) -> list[crawl.Action]:
    """Drop later duplicates by (kind, selector key) so the proposer's choice for an element wins over the deterministic baseline's."""
    seen: set[tuple[str, str]] = set()
    out: list[crawl.Action] = []
    for a in actions:
        k = (a.kind, a.key)
        if k not in seen:
            seen.add(k)
            out.append(a)
    return out


def make_guide(
    report: Report | None = None,
    *,
    ai: AiConfig | None = None,
    redactor: Redactor | None = None,
) -> crawl.Guide:
    """The AI crawl guide, narrating its reasoning through `report`.

    The guide reaches the model through the SDK-based `AiBackend` seam (BE-0104), so the resolved
    `ai` config (BE-0047) picks the provider — Anthropic API, Bedrock, or the Anthropic CLI (`ant`,
    BE-0163). `ai` and `redactor` thread the BE-0047 data-sovereignty guarantees (provider config +
    textual-input redaction) into every AI call the guide makes (BE-0097).
    """
    # Imported in the body, not at module load: the proposer calls three helpers from this module,
    # so rule 5 breaks the cycle the split creates on the factory's single edge back into it.
    from .claude_action_proposer import ClaudeActionProposer

    proposer: ActionProposer = ClaudeActionProposer(ai=ai, redactor=redactor)
    return ai_guide(proposer, report=report, tab_locator=crawl_tabs.ClaudeTabLocator(ai=ai))


def _render_elements(elements: list[base.Element]) -> str:
    """A compact text view of the screen for the model (alongside the screenshot)."""
    return "\n".join(render_elements(elements, compact=True)) or "(no addressable elements)"


def _text_block(
    elements: list[base.Element],
    candidates: list[crawl.Action],
    dismissed: tuple[str, ...],
) -> str:
    """The textual screen description for the model: its elements, the deterministic inspector's operations, and any OS prompt just dismissed to reach it."""
    found = "\n".join(f"- {a.describe()}" for a in candidates) or "(none)"
    text = (
        f"Screen elements:\n{_render_elements(elements)}\n\n"
        f"Operations the deterministic inspector already found here:\n{found}"
    )
    if dismissed:
        text += f"\n\nAn OS prompt was just dismissed to reach this screen (tapped: {', '.join(dismissed)})."
    return text


def _content(
    elements: list[base.Element],
    screenshot: bytes | None,
    candidates: list[crawl.Action],
    dismissed: tuple[str, ...],
    redactor: Redactor | None = None,
) -> list[ContentPart]:
    content: list[ContentPart] = []
    if screenshot:
        content.append(ImagePart(data=screenshot))
    text = _text_block(elements, candidates, dismissed)
    if redactor is not None:
        text = redactor.redact_text(text)
    content.append(TextPart(text=text))
    return content


def _secure_fields(elements: list[base.Element]) -> _SecureFields:
    """The identifiers and labels of the screen's platform-marked masked inputs."""
    marked = [el for el in elements if base.Trait.SECURE_TEXT_FIELD in (el.get("traits") or [])]
    return _SecureFields(
        ids=frozenset(i for el in marked if (i := el.get("identifier"))),
        labels=frozenset(v for el in marked if (v := el.get("label"))),
    )


def _actions_from(payload: dict[str, Any], cap: int, secure: _SecureFields) -> list[crawl.Action]:
    """Turn the tool call's `actions` array into crawl Actions, skipping malformed entries and capping the count so one screen can't blow the step budget."""
    out: list[crawl.Action] = []
    for item in payload.get("actions") or []:
        if not isinstance(item, dict):
            continue
        action = item.get("action")
        if action == "fill":
            pairs = tuple(
                (str(f["id"]), str(f.get("value") or ""))
                for f in (item.get("fields") or [])
                if isinstance(f, dict) and f.get("id")
            )
            if pairs:
                # A fill records one value list, so any secure field among its targets makes the
                # whole action secure — the stricter answer is the one that cannot under-mask.
                out.append(
                    crawl.Action(
                        "fill",
                        fields=pairs,
                        secure=any(secure.covers(fid, None) for fid, _ in pairs),
                    )
                )
        else:
            kind = "type" if action == "type" else "tap"
            target = str(item.get("id") or "")
            label = item.get("label")
            if not target and not label:
                continue  # need a stable selector to replay
            index = item.get("index")
            name = str(label) if label is not None else None
            out.append(
                crawl.Action(
                    kind,
                    target=target,
                    label=name,
                    index=int(index) if isinstance(index, int) else None,
                    value=str(item["value"]) if kind == "type" and item.get("value") else None,
                    secure=secure.covers(target, name),
                )
            )
        if len(out) >= cap:
            break
    return out


def _proposal_from(payload: dict[str, Any], cap: int, secure: _SecureFields) -> Proposal:
    """Build a `Proposal` (actions + the model's `thought`) from the tool call's input."""
    return Proposal(
        actions=_actions_from(payload, cap, secure),
        thought=str(payload.get("thought") or ""),
    )
