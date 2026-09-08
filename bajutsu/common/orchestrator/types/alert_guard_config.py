"""The reactive system-alert guard's per-scenario configuration (BE-0315)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from bajutsu.common.drivers import base

from ._functions import alert_block_note, match_alert_rule, selector_names_button
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

# What a native probe found: "incapable" (backend has no native path), "absent" (no alert — a
# deterministic fact), "dismissed" (a policy-named button was tapped), "unhandled" (an alert is up
# but no rule identifies it, so nothing clears it and the caller reports it instead),
# "reserved" (an alert is up and a waiting `handleSystemAlert` step named it, so this probe leaves
# it for the step's own tap — BE-0406).
NativeAlertState = Literal["incapable", "absent", "dismissed", "unhandled", "reserved"]


@dataclass
class AlertGuardConfig:
    """The reactive system-alert guard's per-scenario configuration and dismiss entry point (BE-0315).

    Callable as the `BlockedHandler` it replaces — `guard(driver)` clears a blocking system alert
    through the deterministic native path (BE-0316's SpringBoard query + `handle_system_alert`) on a
    backend advertising `HANDLE_SYSTEM_ALERT`, or through the in-tree dismiss for an app-owned prompt
    that query cannot see. Every path here is deterministic: BE-0402 removed the AI-vision fallback
    from `run`, so where neither path can act the guard does nothing and records `blocked_note` for
    the blocked step to report. `rules` are the whole policy (BE-0406) — each answers one named
    prompt regardless of which label it shares with another, and an alert no rule identifies is left
    alone rather than answered by a guessed button. `poll_interval` is the native presence-query
    cadence the mid-wait gate polls on, decoupled from the wait's own condition poll.
    """

    rules: list[ResolvedAlertRule] = field(default_factory=list)
    poll_interval: float = DEFAULT_ALERT_POLL_INTERVAL
    # What the most recent `__call__` saw blocking the screen and could not clear, for the end-of-step
    # and `expect` retry to append to the step's own failure reason (BE-0402). Rewritten on every
    # call, never accumulated: it states what the last probe saw, not that a block was ever seen.
    # Safe to hold here because `_guard_for` builds one config per scenario and a scenario's steps run
    # in sequence, so no note crosses a scenario or a worker boundary.
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
        self, driver: base.Driver, reserved: base.Selector | None = None
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

    def dismiss_from_tree_once(self, driver: base.Driver) -> AlertEvent | None:
        """Tap a scenario-named dismiss button visible in the driver's own tree, once.

        The one-shot twin of `_AlertGuardGate._dismiss_from_tree` (waits.py), for the end-of-step and
        `expect` retry. It exists for the same prompt that motivated the mid-wait one: iOS raises its
        "Save Password" alert *inside the app's process*, so `springboard.alerts` never sees it and
        only a tap in the tree can clear it — and measured, such an alert can arrive after a
        scenario's last wait has already returned, where only this path is left to meet it.

        One-shot, so it carries none of the mid-wait version's per-showing bookkeeping (retap delay,
        tap ceiling, decline bound): the caller runs it once per failed step, not per poll, so there
        is no stream to pace. It matches the same narrow surface — an identifier-less labelled button
        on an alert one of the scenario's own in-tree-capable rules identifies, resolving uniquely.

        Returns the `AlertEvent` for the button it tapped, or None when nothing matched, the match was
        ambiguous, or the tap lost a race with the prompt closing itself.
        """
        rules = self.tree_rules
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
        except (base.ElementNotFound, base.AmbiguousSelector, base.ElementNotTappable):
            # The prompt closed itself, or another button of that name appeared, or it is not yet
            # reachable. All three are benign here: this is one opportunistic attempt on a step that
            # has already failed, and the step's own outcome still decides the verdict.
            return None
        return AlertEvent(label=label)

    def __call__(self, driver: base.Driver) -> AlertEvent | None:
        """The end-of-step / expect retry: a one-shot dismiss, or None with `blocked_note` set."""
        state, event, buttons = self.probe_native(driver)
        if state == "dismissed":
            self.blocked_note = ""
            return event
        if state == "absent":
            # No *SpringBoard* alert, which is both the licence to tap an app element (XCUITest
            # answers an interrupting out-of-process alert before synthesizing any interaction) and
            # the case where an app-owned prompt is the remaining explanation for the failed step.
            tree_event = self.dismiss_from_tree_once(driver)
            if tree_event is not None:
                self.blocked_note = ""
                return tree_event
        # "unhandled": an alert is up that no rule identifies. BE-0402 leaves it alone
        # rather than asking a model where to tap, so the step keeps failing — but on its own timeout
        # with the alert named, not as an unexplained missing element. "incapable" and a bare
        # "absent" clear the note instead: neither is evidence of anything blocking the screen.
        self.blocked_note = alert_block_note(buttons) if state == "unhandled" else ""
        return None
