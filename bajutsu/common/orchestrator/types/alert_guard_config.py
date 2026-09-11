"""The reactive system-alert guard's per-scenario configuration (BE-0315)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Literal

from bajutsu.common.drivers import base

from ._functions import (
    alert_block_note,
    matching_alert_rule,
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


def _resolve_alert_rule(
    rules: Sequence[ResolvedAlertRule],
    buttons: Sequence[str],
    dismissed: frozenset[frozenset[str]],
) -> ResolvedAlertRule | None:
    """The rule a round should act on, honoring the same-shape retry `probe_native`,
    `dismiss_from_tree_once`, and `AlertGuardConfig.__call__` (BE-0418) must all agree on bit for
    bit — shared by the native and tree paths alike, since both face the same lingering-fade race.

    The plain match, unless its shape is one `dismissed` already names *or a subset of one* — a
    lingering fade of an already-answered alert, read with a subset of the buttons the dismissing
    round itself matched on — in which case the search retries among the rules whose shape is not
    a subset of any dismissed shape, so a real, not-yet-answered alert enumerable alongside that
    fade (the stacked case this loop exists to clear) is still found rather than declined along
    with the fade. The subset test, not equality, is what keeps a `savePassword`-style policy safe:
    `choice: deny` there resolves to three rules, two of whose shapes nest (the web-form shape
    naming "Save Password", "Never for This Website", and "Not Now"; the iOS 18.6 in-app shape
    naming only "Save Password" and "Not Now" — the 26.5 shape, "Save" and "Not Now", shares
    neither label with the widest and nests with neither), both tapping the same button, and a
    fade that still enumerates the wider shape's buttons would otherwise match the narrower
    sibling and tap it a second time. `__call__`
    calls this again, over the same `buttons` a dismissing round just read, to learn which shape it
    tapped without either probe growing a return member only one caller needs.
    """
    rule = matching_alert_rule(rules, buttons)
    if rule is not None and any(rule.identifying_labels <= shape for shape in dismissed):
        rule = matching_alert_rule(
            [r for r in rules if not any(r.identifying_labels <= shape for shape in dismissed)],
            buttons,
        )
    return rule


@dataclass(frozen=True)
class NotTappable:
    """`dismiss_from_tree_once`'s landing race: the button resolved but the tap could not land.

    Distinguished from `None` ("nothing to do here") so the caller's own round-bounded loop can
    retry the same tap rather than giving up on it (BE-0418) — the in-tree twin of the retry
    `_alert_guard_gate.py` already carries across polls, for the same scrim-over-a-still-animating-
    sheet race. `label` is the tap label `_resolve_alert_rule` already resolved, so a caller that gives
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
        dismissed: frozenset[frozenset[str]] = frozenset(),
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
            dismissed: `identifying_labels` sets naming every rule `__call__` (BE-0418) has
                already dismissed this call, checked *before* tapping — not merely deduplicated
                after the fact — so a lingering fade never reaches a second real tap on the
                device. Keyed on a rule's own shape, not on the raw `buttons` read:
                `system_alert_labels()` enumerates every alert SpringBoard currently holds, so a
                still-fading alert's own button set changes the moment any other alert joins or
                leaves the surface — a `buttons`-keyed dedup would then read it as a genuinely new
                alert and tap it again, precisely the repeat tap this parameter exists to rule
                out. `identifying_labels` rather than `tap_label`, so a scenario's `choice`
                overriding a target's for the same prompt (BE-0177) — two rules sharing one
                alert's shape under different `tap_label`s — still counts as one already-answered
                alert rather than promoting the sibling to tap the opposite button on it. A shape
                that is a *subset* of one already named here counts as the same answered alert
                too, not only an exact match — two rules for the same prompt can nest this way
                (see `dismiss_from_tree_once`'s `exclude` for the concrete, tree-side example;
                `savePassword` never reaches this native-only parameter, since that prompt is
                tree-only). A later alert resolving to a shape that is neither a match nor a
                subset of one already named — including one sharing only the tapped label, like
                `notifications` and `tracking` both tapping `"Allow"` — still taps as usual, once
                it is no longer read alongside the one already named.
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
        native_rules = [r for r in self.rules if r.native]
        if matching_alert_rule(native_rules, buttons) is None:
            return "unhandled", None, list(buttons)
        # A shape does identify the alert, but it may be one this call has already answered,
        # still matching because that alert's own dismiss animation outran `settle` — regardless
        # of what else the SpringBoard surface now enumerates alongside it. `_resolve_alert_rule`
        # retries among the shapes not yet answered in that case, so a real, not-yet-answered
        # alert enumerable alongside the fade (the stacked case this loop exists to clear) is
        # still found rather than declined along with it.
        rule = _resolve_alert_rule(native_rules, buttons, dismissed)
        if rule is None:
            # Every matching shape here is one this call already answered, and a repeat tap would
            # land on nothing (the alert genuinely gone) or on whatever the closing alert has by
            # then revealed underneath it — the same hazard `dismiss_from_tree_once`'s `exclude`
            # closes on the tree side.
            return "already_dismissed", None, list(buttons)
        label = rule.tap_label
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
        self, driver: base.Driver, *, exclude: frozenset[frozenset[str]] = frozenset()
    ) -> tuple[AlertEvent | NotTappable | None, list[str]]:
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

        `exclude` names every shape already dismissed earlier in the same call (BE-0418), via
        `_resolve_alert_rule` — the same shared, post-match lookup `probe_native` uses, and for the
        same two reasons. First, a button that stays in the tree past its own dismiss animation
        would otherwise match again, and tapping it a second time risks landing on an application
        button the closing sheet has by then revealed; declining a repeat match closes that.
        Second, retrying among the shapes not yet excluded — rather than ending the search at the
        first, already-answered match — still finds a real, not-yet-answered alert enumerable
        alongside that fade (the stacked case this loop exists to clear), and keying on
        `identifying_labels` rather than `tap_label` means two rules sharing one alert's shape
        under different choices (a scenario's `choice` overriding a target's for the same prompt,
        BE-0177) are excluded together rather than one promoting the other to tap the opposite
        button on the alert this call already answered. A shape that is a *subset* of one already
        excluded here counts as excluded too, the same as on the native side (`probe_native`'s
        `dismissed`): `savePassword`'s `choice: deny` resolves to three rules, two of whose shapes
        nest (the web-form shape naming "Save Password", "Never for This Website", and "Not Now";
        the iOS 18.6 in-app shape naming only "Save Password" and "Not Now" — the 26.5 shape,
        "Save" and "Not Now", shares neither label with the widest and nests with neither), both
        tapping the same button, and a fade that still enumerates the wider shape's buttons would
        otherwise match the narrower sibling and tap it a second time.

        Returns the `AlertEvent` for the button it tapped, `NotTappable` when the button resolved but
        the tap could not land — a scrim still covering it mid-animation, which the caller's own
        round-bounded loop retries — or None when nothing not-yet-excluded matched, the match was
        ambiguous, or the tap lost a race with the prompt closing itself; alongside it, the buttons
        this round's own tree read found, so a caller can resolve the same match again to learn
        which shape a returned `AlertEvent` belongs to.
        """
        rules = self.tree_rules
        if not rules:
            return None, []
        elements = driver.query()
        buttons = [
            el["label"]
            for el in elements
            if el["label"] and not el["identifier"] and base.Trait.BUTTON in el["traits"]
        ]
        rule = _resolve_alert_rule(rules, buttons, exclude)
        if rule is None:
            return None, buttons
        label = rule.tap_label
        # The same uniqueness pre-check the mid-wait path applies: a bare `{"label": label}` selector
        # ignores traits, so an identified app button of the same name would make the tap ambiguous.
        if (
            sum(1 for el in elements if el["label"] == label and base.Trait.BUTTON in el["traits"])
            != 1
        ):
            return None, buttons
        try:
            driver.tap({"label": label, "traits": [base.Trait.BUTTON]})
        except (base.ElementNotFound, base.AmbiguousSelector):
            # The prompt closed itself, or another button of that name appeared. Both benign here:
            # this is one opportunistic attempt on a step that has already failed, and the step's own
            # outcome still decides the verdict.
            return None, buttons
        except base.ElementNotTappable:
            # Visible but not yet reachable — a scrim the sheet draws over its own button before
            # finishing its presentation animation. Not a reason to give up: the caller's own
            # round-bounded loop retries the same tap, mirroring the mid-wait path's own retry for
            # this exception (BE-0418).
            return NotTappable(label=label), buttons
        return AlertEvent(label=label), buttons

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

        `settle` runs after every round that acted on a live alert — one that dismissed something,
        one that found a button not yet tappable, and one that declined a still-fading alert it
        had already dismissed — the caller's own `settle_after_alert_dismiss` bound to its
        `clock`/`transitions`/`cancelled`, including the round that exhausts the bound, so a
        caller reading the screen right after this call returns never reads one still
        mid-animation. `settle` is best-effort and bounded, though: a dismiss whose animation
        outlasts it can still be up, unchanged, on a later round's read, and neither path re-taps
        it. Both pass every shape (a rule's `identifying_labels`) they have already dismissed this
        call into `_resolve_alert_rule` (shared with `probe_native` and `dismiss_from_tree_once`),
        which retries among the shapes not yet dismissed before declining a match that lands back
        on one of them — the same alert still fading, even a round or two after a *different*
        alert cleared in between, rather than a second real tap on the device that risks landing
        on nothing or on whatever the closing alert has by then revealed underneath it. Keyed on a
        rule's own shape rather than the raw buttons a probe reads, since that read enumerates
        every alert the surface currently holds and so changes the moment a different alert joins
        or leaves it, which the alert already dismissed did not do — and rather than a rule's own
        `tap_label`, since two rules can share one alert's shape under different choices (a
        scenario's `choice` overriding a target's for the same prompt, BE-0177), and keying on the
        label alone would let one such rule's exclusion promote its sibling to tap the opposite
        button on the same alert. A later alert resolving to a genuinely different shape, once the
        earlier one is no longer part of what a probe reads, still taps as usual on either path —
        including one sharing only the tapped label (`notifications` and `tracking` both grant
        `"Allow"`). Two such shapes enumerable *together* instead share that label's count, so
        `matching_alert_rule`'s own per-label uniqueness check (`_functions.py`) matches neither
        until the read no longer holds both, and the round reports the surface as unhandled rather
        than guessing which one a shared label answers for.

        `note` likewise survives a round that resolves a *different* surface: a tree button stuck
        behind a scrim (`NotTappable`) stays named in the eventual `blocked_note` even if a later
        round goes on to dismiss an unrelated SpringBoard alert, rather than that unrelated success
        silently erasing a diagnosis the tree round still stands by.
        """
        cleared = False
        note = ""
        tree_note_pending = False
        dismissed_native: frozenset[frozenset[str]] = frozenset()
        dismissed_tree_shapes: frozenset[frozenset[str]] = frozenset()
        for _ in range(_GUARD_CALL_MAX_ROUNDS):
            state, event, buttons = self.probe_native(driver, dismissed=dismissed_native)
            if state == "dismissed":
                assert event is not None  # "dismissed" always carries its event (see probe_native)
                alerts.append(event)  # never a repeat: probe_native declined an already-seen key
                # Re-resolves which shape `probe_native` just tapped, over the same `buttons` it
                # already read this round, via the identical shared lookup — rather than add a
                # return member only this one caller needs — so this always agrees with what
                # `probe_native` actually acted on, including when the plain first match was
                # itself already answered and the tap landed on its not-yet-answered fallback.
                rule = _resolve_alert_rule(
                    [r for r in self.rules if r.native], buttons, dismissed_native
                )
                assert rule is not None  # the round that just dismissed this alert matched it
                dismissed_native |= {rule.identifying_labels}
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
                    # `buttons` is the whole enumerable SpringBoard surface, not this one rule's
                    # own set, so declining a re-tap here does not mean nothing else is up: a
                    # second, still-live alert no rule identifies can sit right alongside it. Only
                    # the labels of rules this call has already answered are accounted for;
                    # anything else on the surface gets the same diagnosis a fresh "unhandled"
                    # probe would give it — the "dismissed" branch's own clear above self-corrects
                    # on a later round that re-probes fresh buttons, but a round that keeps
                    # declining the same rule never does, so it must check this itself.
                    answered = {label for labels in dismissed_native for label in labels}
                    leftover = [b for b in buttons if b not in answered]
                    note = alert_block_note(leftover) if leftover else ""
                settle()
                continue
            if state == "absent":
                # No *SpringBoard* alert, which is both the licence to tap an app element (XCUITest
                # answers an interrupting out-of-process alert before synthesizing any interaction)
                # and the case where an app-owned prompt is the remaining explanation for the block.
                tree_result, tree_buttons = self.dismiss_from_tree_once(
                    driver, exclude=dismissed_tree_shapes
                )
                if isinstance(tree_result, AlertEvent):
                    alerts.append(tree_result)  # excluded once cleared, so never a repeat report
                    # Re-resolves which shape was just tapped, over the same `buttons` this round's
                    # own tree read already found, the same way the native branch above does.
                    rule = _resolve_alert_rule(self.tree_rules, tree_buttons, dismissed_tree_shapes)
                    assert rule is not None  # the round that just dismissed this alert matched it
                    dismissed_tree_shapes |= {rule.identifying_labels}
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
                # Nothing not-yet-excluded matched. A shape this call already cleared, still
                # enumerable among this round's own tree read, is the in-tree twin of
                # `probe_native`'s "already_dismissed": the sheet's own fade outlasted `settle`, so
                # settle again and give a sheet stacked underneath it another round to be
                # presented, rather than ending the call on a lingering fade this loop exists to
                # see past.
                if any(shape <= set(tree_buttons) for shape in dismissed_tree_shapes):
                    settle()
                    continue
                # Otherwise this round's tree read may simply have caught a still-animating screen
                # mid-transition rather than a genuinely clear one, so `note` is left as an earlier
                # round's diagnosis left it rather than erased on this round's own account.
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
