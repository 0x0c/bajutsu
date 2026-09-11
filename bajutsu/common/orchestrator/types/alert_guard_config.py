"""The reactive system-alert guard's per-scenario configuration (BE-0315)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal

from bajutsu.common.drivers import base

from ._functions import (
    alert_block_note,
    match_alert_rule,
    selector_names_button,
    uncleared_prompt_note,
)
from .alert_event import AlertEvent
from .resolved_alert_rule import ResolvedAlertRule

# The reactive guard's default native presence-query cadence (seconds), overridable per scenario /
# target / flag via `systemAlertHandling.pollInterval` (BE-0315, riding the BE-0177 precedence).
DEFAULT_ALERT_POLL_INTERVAL = 1.0

# The timeout the reactive guard passes `handle_system_alert` for its tap (BE-0315): 0 means "query
# SpringBoard once and tap if the button is present, else fail fast" — the guard has already observed
# the alert via `system_alert_labels`, so it never waits for one to appear (that is the proactive
# `handleSystemAlert` step's job), and a vanish-between-query-and-tap race fails fast rather than
# blocking the mid-wait poll.
_NATIVE_TAP_TIMEOUT = 0.0

# The end-of-step / expect call's own round bound (BE-0418). Unlike the mid-wait gate, this call
# gets no poll cycle of its own to loop on, so `__call__` loops internally instead. Matches
# `_TREE_DISMISS_MAX_TAPS` (`_alert_guard_gate.py`), the mid-wait path's own tap ceiling for the
# same landing-race retry (BE-0418 Unit 2).
_GUARD_CALL_MAX_ROUNDS = 3

# What a native probe found: "incapable" (backend has no native path), "absent" (no alert — a
# deterministic fact), "dismissed" (a policy-named button was tapped), "unhandled" (an alert is up
# but no rule identifies it, so nothing clears it and the caller reports it instead),
# "reserved" (an alert is up and a waiting `handleSystemAlert` step named it, so this probe leaves
# it for the step's own tap — BE-0406), "already_dismissed" (the alert this round would tap is one
# `__call__` already dismissed earlier this call, still enumerable because its fade outlasted
# `settle` — declined without tapping, since a repeat tap under this dedup's own premise can only
# land on nothing (the alert genuinely gone) or on whatever the closing alert has by then revealed
# underneath it — BE-0418).
NativeAlertState = Literal[
    "incapable", "absent", "dismissed", "unhandled", "reserved", "already_dismissed"
]


@dataclass(frozen=True)
class NotTappable:
    """`dismiss_from_tree_once`'s landing race: the button resolved but the tap could not land.

    Distinguished from `None` ("nothing to do here") so the caller's own round-bounded loop can
    retry the same tap rather than giving up on it (BE-0418) — the in-tree twin of the retry
    `_alert_guard_gate.py` already carries across polls, for the same scrim-over-a-still-animating-
    sheet race. `label` is the tap label `match_alert_rule` already resolved, so a caller that gives
    up can name it in `uncleared_prompt_note` without resolving it a second time.
    """

    label: str


@dataclass
class AlertGuardConfig:
    """The reactive system-alert guard's per-scenario configuration and dismiss entry point (BE-0315).

    `guard(driver, alerts, settle=...)` clears whatever blocks the screen, across up to
    `_GUARD_CALL_MAX_ROUNDS` rounds (BE-0418), through the deterministic native path (BE-0316's
    SpringBoard query + `handle_system_alert`) on a backend advertising `HANDLE_SYSTEM_ALERT`, the
    in-tree dismiss for an app-owned prompt that query cannot see, or both in the same call when one
    sits stacked in front of the other. Every path here is deterministic: BE-0402 removed the
    AI-vision fallback from `run`, so where neither path can act the guard does nothing and records
    `blocked_note` for the blocked step to report. `rules` are the whole policy (BE-0406) — each
    answers one named prompt regardless of which label it shares with another, and an alert no rule
    identifies is left alone rather than answered by a guessed button. `poll_interval` is the native
    presence-query cadence the mid-wait gate polls on, decoupled from the wait's own condition poll.
    """

    rules: list[ResolvedAlertRule] = field(default_factory=list)
    poll_interval: float = DEFAULT_ALERT_POLL_INTERVAL
    # What the most recent `__call__` saw blocking the screen and could not clear, for the end-of-step
    # and `expect` retry to append to the step's own failure reason (BE-0402). Rewritten on every
    # call, never accumulated across calls: it states what this call's rounds (BE-0418) saw, not that
    # a block was ever seen on some earlier step. Within a call each round overwrites what the one
    # before it found, except a round that matches nothing at all — see `__call__`. Safe to hold here
    # because `_guard_for` builds one config per scenario and a scenario's steps run in sequence, so
    # no note crosses a scenario or a worker boundary.
    blocked_note: str = field(default="", init=False)

    @property
    def tree_rules(self) -> list[ResolvedAlertRule]:
        """The rules the in-tree dismissal may act on: those whose prompt that path can reach.

        Arming on *any* rule would widen the tree match past what the author asked for — a scenario
        declaring `notifications` alone would arm one for a prompt that only ever appears in
        SpringBoard, and an application screen happening to show identifier-less "Allow" and
        "Don't Allow" buttons would be tapped (BE-0406).
        """
        return [rule for rule in self.rules if rule.in_tree]

    def probe_native(
        self,
        driver: base.Driver,
        reserved: base.Selector | None = None,
        *,
        dismissed: frozenset[tuple[str, tuple[str, ...]]] = frozenset(),
    ) -> tuple[NativeAlertState, AlertEvent | None, list[str]]:
        """Query and, where possible, clear a system alert natively; report what happened.

        Reads BE-0316's SpringBoard query (`system_alert_labels`) to learn the alert's buttons, picks
        the button a `rules` entry names for the prompt it identifies, and taps it through BE-0316's
        `handle_system_alert`. The returned `AlertEvent` is set only for
        `"dismissed"`. `"absent"` is a deterministic no-*SpringBoard*-alert fact — but the native query
        only sees `springboard.alerts`, so a non-enumerable surface (an action sheet, a WKWebView
        dialog) reads as `"absent"` too, and only the mid-wait gate's debounced collapsed-tree proxy
        can notice it. `"unhandled"` means an alert is up but no rule identifies it, so nothing here
        can clear it.

        The third member carries the buttons this query actually read, empty unless an alert was
        seen. `"unhandled"` is the state that needs them: BE-0402 left that alert on screen, so the
        labels are all a blocked step or wait has to name what stopped it, and they would otherwise
        be discarded here. Returned rather than re-queried at that moment, since a second
        cross-process query costs another round trip on the runner's single main thread and reopens
        the time-of-check/time-of-use window the dismiss-race branches below exist to close.

        Args:
            reserved: A waiting `handleSystemAlert` step's own selector, when one is running
                (BE-0406). An alert it names is left untouched — see `selector_names_button`.
            dismissed: `(label, buttons)` pairs `__call__` (BE-0418) has already dismissed this
                call, checked *before* tapping — not merely deduplicated after the fact — so a
                lingering fade never reaches a second real tap on the device. An alert whose full
                button set no longer matches any entry here (buttons changed) is a genuinely new
                alert and taps as usual, even if it happens to share the tapped label. `buttons`
                is `system_alert_labels()`'s own read, which enumerates every alert SpringBoard
                currently holds, not one alert's own set — so this key is a property of the whole
                enumerable surface at read time, and two genuinely distinct stacked alerts with
                disjoint labels would share one key while both are up. `match_alert_rule`'s own
                exact-count requirement already declines an ambiguous shared label as `"unhandled"`
                rather than guessing, and the caller's `settle` narrows the window further by
                letting a fading alert actually clear before the next round reads the surface again.
        """
        if base.Capability.HANDLE_SYSTEM_ALERT not in driver.capabilities():
            return "incapable", None, []
        buttons = driver.system_alert_labels()
        if not buttons:
            return "absent", None, []
        if reserved is not None and selector_names_button(reserved, buttons):
            # The step is waiting on this very alert and taps it on its own next read. Not
            # "absent": an alert *is* up, and "absent" is the one answer licensing an in-tree tap.
            return "reserved", None, list(buttons)
        # Filtered to `native`, not the full `self.rules`: an in-tree-only shape's identifying
        # labels are ordinary vocabulary a real SpringBoard alert could coincidentally offer (the
        # 26.5 save sheet's shape is just "Save" / "Not Now"), and matching it here would answer
        # through `handle_system_alert` a prompt that surface can never actually reach — the same
        # undeclared-screen tap this proposal removes everywhere else (BE-0406).
        label = match_alert_rule([rule for rule in self.rules if rule.native], buttons)
        if label is None:
            return "unhandled", None, list(buttons)
        if (label, tuple(buttons)) in dismissed:
            # The exact alert a previous round already tapped, still enumerable because its own
            # dismiss animation outran `settle`. A repeat tap here would land on nothing (the
            # alert genuinely gone) or on whatever the closing alert has by then revealed
            # underneath it — the same hazard `dismiss_from_tree_once`'s `exclude` closes on the
            # tree side, closed here by never tapping at all rather than tapping and discarding
            # the report.
            return "already_dismissed", None, list(buttons)
        try:
            driver.handle_system_alert({"label": label}, _NATIVE_TAP_TIMEOUT)
        except base.ElementNotFound:
            # A time-of-check/time-of-use race: the alert vanished between the presence query and the
            # tap. It is no longer blocking, so treat it as absent rather than failing the step on a
            # benign, self-resolved race — a genuine channel error still propagates.
            return "absent", None, []
        except base.AmbiguousSelector:
            # The other half of that race, and *not* the same answer: the alert is still up, now
            # offering the label twice. Reporting "absent" would say no system alert is showing,
            # which is the one thing licensing an in-tree tap (`_observe_native`'s `probed_absent`) —
            # and that tap, made under a live alert, is what XCUITest answers with its own default
            # button. "unhandled" is what this already is by definition: an alert is up but no rule
            # resolves, so it licenses nothing and is reported instead.
            return "unhandled", None, list(buttons)
        return "dismissed", AlertEvent(label=label), list(buttons)

    def dismiss_from_tree_once(
        self, driver: base.Driver, *, exclude: frozenset[str] = frozenset()
    ) -> AlertEvent | NotTappable | None:
        """Tap a scenario-named dismiss button visible in the driver's own tree, once.

        The one-shot twin of `_AlertGuardGate._dismiss_from_tree` (waits.py), for the end-of-step and
        `expect` retry. It exists for the same prompt that motivated the mid-wait one: iOS raises its
        "Save Password" alert *inside the app's process*, so `springboard.alerts` never sees it and
        only a tap in the tree can clear it — and measured, such an alert can arrive after a
        scenario's last wait has already returned, where only this path is left to meet it.

        Called once per round of the caller's own loop rather than per poll, so it carries none of
        the mid-wait version's per-showing bookkeeping (retap delay, tap ceiling, decline bound) —
        the round bound already serves that purpose (BE-0418). It matches the same narrow surface —
        an identifier-less labelled button on an alert one of the scenario's own in-tree-capable
        rules identifies, resolving uniquely.

        `exclude` withholds a rule already dismissed earlier in the same call (BE-0418): a button
        that stays in the tree past its own dismiss animation would otherwise match again, and
        tapping it a second time risks landing on an application button the closing sheet has by
        then revealed — the same false "tap did not land" the mid-wait path's own `_tree_signature`
        comparison exists to avoid, without needing that comparison here: a label this call has
        already cleared has nothing left for a second tap to usefully answer.

        Returns the `AlertEvent` for the button it tapped, `NotTappable` when the button resolved but
        the tap could not land — a scrim still covering it mid-animation, which the caller's own
        round-bounded loop retries — or None when nothing matched (including a matching label already
        excluded), the match was ambiguous, or the tap lost a race with the prompt closing itself.
        """
        rules = [rule for rule in self.tree_rules if rule.tap_label not in exclude]
        if not rules:
            return None
        elements = driver.query()
        buttons = [
            el["label"]
            for el in elements
            if el["label"] and not el["identifier"] and base.Trait.BUTTON in el["traits"]
        ]
        label = match_alert_rule(rules, buttons)
        if label is None:
            return None
        # The same uniqueness pre-check the mid-wait path applies: a bare `{"label": label}` selector
        # ignores traits, so an identified app button of the same name would make the tap ambiguous.
        if (
            sum(1 for el in elements if el["label"] == label and base.Trait.BUTTON in el["traits"])
            != 1
        ):
            return None
        try:
            driver.tap({"label": label, "traits": [base.Trait.BUTTON]})
        except (base.ElementNotFound, base.AmbiguousSelector):
            # The prompt closed itself, or another button of that name appeared. Both benign here:
            # this is one opportunistic attempt on a step that has already failed, and the step's own
            # outcome still decides the verdict.
            return None
        except base.ElementNotTappable:
            # Visible but not yet reachable — a scrim the sheet draws over its own button before
            # finishing its presentation animation. Not a reason to give up: the caller's own
            # round-bounded loop retries the same tap, mirroring the mid-wait path's own retry for
            # this exception (BE-0418).
            return NotTappable(label=label)
        return AlertEvent(label=label)

    def __call__(
        self,
        driver: base.Driver,
        alerts: list[AlertEvent],
        *,
        settle: Callable[[], None],
    ) -> bool:
        """The end-of-step / expect retry: dismiss whatever blocks the screen, in bounded rounds.

        Loops up to `_GUARD_CALL_MAX_ROUNDS` times (BE-0418), appending every `AlertEvent` it clears
        to `alerts` — the same contract `_AlertGuardGate` already uses — rather than returning one,
        since a multi-round call can dismiss more than a single `AlertEvent | None` could report: a
        stacked SpringBoard prompt and an app-owned sheet underneath it can both clear in one call.
        Returns whether anything was cleared at all, which is what the caller's own one-shot retry
        gates on; `blocked_note` can still be non-empty on a `True` return — an earlier round can
        clear a stacked alert while a later one leaves a second unhandled, and the caller reports both
        facts rather than treating them as mutually exclusive.

        `settle` runs after every round that dismissed something or found a button not yet tappable
        — the caller's own `settle_after_alert_dismiss` bound to its `clock`/`transitions`/
        `cancelled` — including the round that exhausts the bound, so a caller reading the screen
        right after this call returns never reads one still mid-animation. `settle` is best-effort
        and bounded, though: a dismiss whose animation outlasts it can still be up, unchanged, on a
        later round's read, and neither path re-taps it. The native one passes every `(label,
        buttons)` pair it has already dismissed this call into `probe_native`, which declines to
        tap a match already in that set — the same alert still fading, even a round or two after a
        *different* alert cleared in between, rather than a second real tap on the device that
        risks landing on whatever the closing alert has by then revealed underneath it. A later
        alert sharing only the tapped label (`notifications` and `tracking` both grant `"Allow"`)
        still differs on the buttons it offers and taps as usual. The tree one withholds a label it
        has already cleared from matching at all, so there too the second tap never happens (see
        `dismiss_from_tree_once`).

        `note` likewise survives a round that resolves a *different* surface: a tree button stuck
        behind a scrim (`NotTappable`) stays named in the eventual `blocked_note` even if a later
        round goes on to dismiss an unrelated SpringBoard alert, rather than that unrelated success
        silently erasing a diagnosis the tree round still stands by.
        """
        cleared = False
        note = ""
        tree_note_pending = False
        dismissed_native: frozenset[tuple[str, tuple[str, ...]]] = frozenset()
        dismissed_tree_labels: frozenset[str] = frozenset()
        for _ in range(_GUARD_CALL_MAX_ROUNDS):
            state, event, buttons = self.probe_native(driver, dismissed=dismissed_native)
            if state == "dismissed":
                assert event is not None  # "dismissed" always carries its event (see probe_native)
                alerts.append(event)  # never a repeat: probe_native declined an already-seen key
                dismissed_native |= {(event.label, tuple(buttons))}
                cleared = True
                if not tree_note_pending:
                    note = ""
                settle()
                continue
            if state == "already_dismissed":
                # The same lingering alert `dismissed` already named — probe_native declined the
                # tap outright, so nothing was actuated this round. Still settle: this round just
                # enumerated a live alert mid-fade, both call sites read the screen the instant
                # this returns, and letting the fade run down here is what lets a later round
                # reach "absent" — and any app-owned sheet stacked underneath — instead of
                # spending the whole bound re-reading the same alert.
                if not tree_note_pending:
                    note = ""
                settle()
                continue
            if state == "absent":
                # No *SpringBoard* alert, which is both the licence to tap an app element (XCUITest
                # answers an interrupting out-of-process alert before synthesizing any interaction)
                # and the case where an app-owned prompt is the remaining explanation for the block.
                tree_result = self.dismiss_from_tree_once(driver, exclude=dismissed_tree_labels)
                if isinstance(tree_result, AlertEvent):
                    alerts.append(tree_result)  # excluded once cleared, so never a repeat report
                    dismissed_tree_labels |= {tree_result.label}
                    cleared = True
                    note = ""
                    tree_note_pending = False
                    settle()
                    continue
                if isinstance(tree_result, NotTappable):
                    note = uncleared_prompt_note(tree_result.label)
                    tree_note_pending = True
                    settle()
                    continue
                # Nothing matched. This round's tree read may simply have caught a still-animating
                # screen mid-transition rather than a genuinely clear one, so `note` is left as an
                # earlier round's diagnosis left it rather than erased on this round's own account.
                break
            # "unhandled": an alert is up that no rule identifies. BE-0402 leaves it alone rather
            # than asking a model where to tap, so the step keeps failing — but on its own timeout
            # with the alert named, not as an unexplained missing element. "reserved" and
            # "incapable" clear the note instead: neither is evidence of anything blocking the
            # screen that this call could have acted on. Both are also driver facts fixed for the
            # whole call (a capability, or a step's own reserved selector — never passed here, so
            # "reserved" cannot actually occur from this call site), so neither can follow a round
            # that already found something concerning.
            note = alert_block_note(buttons) if state == "unhandled" else ""
            break
        self.blocked_note = note
        return cleared
