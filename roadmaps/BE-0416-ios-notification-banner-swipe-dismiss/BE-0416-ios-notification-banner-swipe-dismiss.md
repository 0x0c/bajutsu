**English** · [日本語](BE-0416-ios-notification-banner-swipe-dismiss-ja.md)

# BE-0416 — Swipe away an interrupting iOS notification banner reactively

<!-- BE-METADATA -->
| Field | Value |
|---|---|
| Proposal | [BE-0416](BE-0416-ios-notification-banner-swipe-dismiss.md) |
| Author | [@0x0c](https://github.com/0x0c) |
| Status | **Proposal** |
| Tracking issue | [Search](https://github.com/bajutsu-e2e/bajutsu/issues?q=is%3Aissue+label%3Aroadmap-tracking+in%3Atitle+"BE-0416") |
| Topic | Platform support |
| Related | [BE-0177](../BE-0177-run-behavior-target-config/BE-0177-run-behavior-target-config.md), [BE-0314](../BE-0314-scenario-interrupt-handlers/BE-0314-scenario-interrupt-handlers.md), [BE-0315](../BE-0315-ios-native-system-alert-handling/BE-0315-ios-native-system-alert-handling.md), [BE-0399](../BE-0399-ios-system-alert-interruption-policy/BE-0399-ios-system-alert-interruption-policy.md), [BE-0406](../BE-0406-system-alert-declared-prompts/BE-0406-system-alert-declared-prompts.md) |
<!-- /BE-METADATA -->

## Introduction

Bajutsu already clears two kinds of interstitial iOS screen without asking a model. An interstitial
the application's own accessibility tree can see gets a condition-and-recovery entry in the
`interrupts` field ([BE-0314](../BE-0314-scenario-interrupt-handlers/BE-0314-scenario-interrupt-handlers.md)).
An operating-system alert the tree cannot see gets a native SpringBoard query and a per-prompt
policy ([BE-0315](../BE-0315-ios-native-system-alert-handling/BE-0315-ios-native-system-alert-handling.md),
[BE-0399](../BE-0399-ios-system-alert-interruption-policy/BE-0399-ios-system-alert-interruption-policy.md),
[BE-0406](../BE-0406-system-alert-declared-prompts/BE-0406-system-alert-declared-prompts.md)). Neither
path reaches a third kind of interstitial: the banner iOS raises over the running app when a push or
local notification arrives while the app is in the foreground. This proposal adds a native presence
query and a swipe-based dismiss action for that banner, wired into the reactive-guard shape BE-0315
established for system alerts, so a step's tap lands on the element the scenario names instead of on
a banner the scenario never declared.

## Motivation

A foreground notification banner can appear at any point in a run, and it can sit directly over the
element a step is about to tap. In a real run, the banner has no fixed trigger a scenario can place a
check after: a push notification's arrival depends on a server, and even a local notification an app
schedules for itself lands relative to wall-clock time, not relative to any step. A step whose target
happens to sit under the banner's frame can therefore tap the banner instead of the target, or resolve
against whichever element XCUITest's own hit-testing picks once the overlap is present — a defect that
reads as flakiness, since nothing in the run's report records that a banner ever appeared.

The gap is structural, not incidental. A process outside the application under test draws the banner,
the same separation BE-0315's motivation measured for a SpringBoard alert, so the `interrupts` field's
condition — evaluated only against the application's own tree — has nothing to check against. And the
banner carries no button: the deterministic dismiss BE-0315 built for a system alert resolves a button
by its label, but a person clears a real banner with an upward swipe, not a tap, and tapping it instead
opens the notification's own app and navigates the run away from the scenario it was running. The
gesture this proposal needs already exists in Bajutsu — `swipe` (documented in
[`docs/scenarios.md`](../../docs/scenarios.md) in both a directional and a coordinate form) — but no
existing mechanism knows where the banner is or when to reach for it.

A later reader can tell whether this proposal arrived by running a scenario that raises the banner with
a `push` step immediately before a tap, so the banner's measured frame overlaps that tap's target by
construction rather than by timing. Before this proposal, that tap is unreliable: where it lands
depends on how the two frames overlap at the moment XCUITest resolves it. After this proposal, the
guard clears the banner before the tap executes, and the tap lands on the target.

## Detailed design

### Unit 1 — measure the banner's accessibility surface on a device

Before any driver method is added, measure how a foreground notification banner actually appears to
XCUITest, on a booted Simulator, across the iOS versions the existing system-alert work already covers
(18.6, 26.3, 26.4, 26.5). This measurement answers six questions. Five of them decide the shape of
every later unit:

1. Which process's element tree exposes the banner — SpringBoard, as with a system alert, or a distinct
   process.
2. What frame or identifier the banner offers, if any.
3. What the presence query enumerates when a scenario raises two banners at once — separately
   measurable frames a guard can order, or frames that coincide with no ordering signal between them.
4. Whether an ordinary `tap`/`type` step already receives XCUITest's own interruption-monitor treatment
   when its target sits under the banner's frame, the treatment BE-0399 measured for a system alert, or
   whether hit-testing instead resolves the overlap silently, with no interruption dispatched at all.
5. Only if the monitor is invoked, whether a swipe issued from inside its handler can be confirmed to
   have cleared the banner before the handler returns `true` — XCUITest checks the interruption only
   after the handler returns, and re-invokes the monitor when it finds the banner still up.

The sixth question is independent of this proposal, detailed next.

BE-0399's monitor is already installed on every run with `systemAlertHandling` on. Its decline of an
interruption it cannot match hands the alert to XCUITest's own default handler, which clears it by
pressing the alert's default button — but a banner has no button for that handler to press. So, if the
fourth fact confirms a banner reaches the monitor, the sixth question is whether that already
reproduces BE-0399's own measured reinvocation loop today, with no code from this proposal involved. A
monitor that claims an interruption it cannot confirm cleared gets re-invoked on every following
interaction, and that looped until the runner died in every attempt BE-0399 measured. A confirmed loop
there is an existing defect this item did not create, and it should be reported on its own regardless
of whether this item
proceeds. This unit produces no code; the measurement fixes the design questions Unit 4 currently
leaves open.

### Unit 2 — a deterministic presence query

Add a driver method that reports whether a notification banner is currently showing and, when one is,
the on-screen frame the swipe in Unit 3 needs. This mirrors the shape of BE-0315's
`system_alert_labels()`: a thin, non-blocking read that reports a fact and decides nothing. The method
sits behind its own capability token, the way `HANDLE_SYSTEM_ALERT` gates BE-0315's query: only the iOS
XCUITest backend advertises it at first, and a backend without it reports absence rather than an error.
When more than one banner is on screen at once, the query's behavior follows Unit 1's third fact.
Concurrent iOS banners typically stack at the same on-screen position, so a shared frame already names
the correct swipe target regardless of which specific banner element the query happened to enumerate —
the guard swipes it, re-polls, and repeats for whatever remains, the same one-per-poll flow Units 3 and
4 already describe. If Unit 1 instead finds concurrent banners at genuinely different, non-overlapping
frames, the query reports the topmost by that frame — a stated, deterministic order (prime directive 2)
rather than whichever banner XCUITest happens to report first — so the guard can dismiss it and re-poll
for the next, rather than aborting a run over an interruption it can clear.

### Unit 3 — a deterministic swipe-dismiss action

Add a driver action that swipes the banner away, anchored to the frame Unit 2 reports rather than a
fixed screen coordinate, so the gesture holds across device sizes. The direction matches how a person
dismisses a real banner: upward, toward the top of the screen, ending at an on-screen point above the
banner's own frame rather than past the screen's edge. The action reuses the coordinate machinery
`swipe`'s existing driver implementation already has, rather than adding a second gesture primitive;
because that machinery resolves a point as an offset from the application's own origin, this unit also
states how the frame Unit 2 reports — measured in the banner-owning process's coordinate space —
converts into it. Because Unit 2 always reports at most one banner — the topmost, when several are stacked — the action
always dismisses the single frame it receives; a guard that finds more than one banner clears them one
poll at a time rather than in a single action.

### Unit 4 — reactive wiring

A config- and scenario-level toggle arms a guard that polls Unit 2's presence query on the bounded
interval BE-0315 already established for the SpringBoard probe, and dismisses the banner through
Unit 3's action the moment one is found. Unit 1's fifth measurement decides which of two paths the
guard takes, and the choice is not symmetric: only one of them is safe to take unconditionally. When
Unit 1 confirms that the handler can swipe the banner away and see it gone before it returns `true`,
the guard answers through that monitor, mirroring how BE-0399's
monitor answers an interrupting alert. That monitor path is available only when `systemAlertHandling`
is also on: it is the single global monitor BE-0399 installed, gated by `policy.governs`, which only
`systemAlertHandling` sets. With `systemAlertHandling` off, the banner toggle never reaches that
monitor and always takes the fallback below, regardless of what Unit 1 found. In every other case —
including when Unit 1 cannot confirm that guarantee — the guard instead polls and clears the banner
immediately before each act step's own actuation. It then re-issues the presence query once more after
its own swipe and waits for it to report the banner gone before letting the step's tap fire. A swipe is
not instantaneous, and a tap synthesized the moment the drag lifts can still land on a banner whose
dismissal animation is still running. That
pre-actuation check issues its own presence query at the step boundary rather than reusing the
interval-bounded poll's last answer, since acting on a remembered probe result is the defect BE-0399
measured. That fallback carries a known, accepted limitation: a banner arriving in the gap between the
poll and the tap's own synthesis can still intercept the tap, so this item does not claim the tap always
lands, only that it lands far more reliably than today. Closing that residual gap is left to a
follow-up rather than blocking this item. Either branch records the dismissal on the step it
interrupted, folded into that step's `AlertEvent`s the same way BE-0399's drained labels are. Because
the banner carries no button, that record needs a field of its own to be legible: `AlertEvent` carries
only `label` — the button the guard tapped, empty when none was named — and the report serializes only
that field, so a banner dismissal would arrive as an empty label, the shape an alert with no named
button already has. This unit adds an optional discriminator to `AlertEvent`, defaulting to today's
alert case so no existing report changes, and a banner dismissal is identifiable in the run's report
rather than merely present. The guard is armed only on a
backend that advertises the capability Unit 2 and Unit 3 gate their driver calls behind; on a backend
without it, the toggle has no effect and today's behavior is unchanged. The toggle follows the same
config-then-scenario, flag-overridable precedence
([BE-0177](../BE-0177-run-behavior-target-config/BE-0177-run-behavior-target-config.md)) that
`systemAlertHandling` and its `--system-alert-handling` CLI flag already established.

### Unit 5 — showcase fixture and on-device verification

Add a showcase scenario that raises the banner with a `push` step
([`docs/scenarios.md`](../../docs/scenarios.md), `simctl push`) placed immediately before the tap under
test, so the banner's arrival is requested at a step boundary rather than at wall-clock timing. Assert
both that the tap lands on that target and that the run's report carries the banner-dismissal
discriminator Unit 4 adds. `simctl push` returns once the payload reaches the device, not once the
banner is actually on screen. A run in which the banner never appeared would otherwise pass on the tap
alone, exercising nothing; asserting on the discriminator closes that gap. Raising the banner is
app-side work this unit owns: the
showcase apps present no foreground banner today —
[`demos/showcase/scenarios/push.yaml`](../../demos/showcase/scenarios/push.yaml) records that its
`push` leaves the foreground UI unchanged — so this unit also adds the
`UNUserNotificationCenterDelegate` foreground presentation the banner needs, and answers the
notification-authorization prompt in the fixture with a `handleSystemAlert` step, since `permissions`
cannot pre-grant notification authorization on iOS ([`docs/scenarios.md`](../../docs/scenarios.md)).
The tap under test must sit inside the frame Unit 1 measured for the banner, so the overlap holds by
construction; if no showcase control does, this unit adds one. The off-Simulator gate cannot prove a
native swipe against a real banner; the unit that lands the
driver methods must exercise this scenario on a booted Simulator.

### Unit 6 — docs

Document the new toggle in [`docs/scenarios.md`](../../docs/scenarios.md), its CLI flag in
[`docs/cli.md`](../../docs/cli.md), and both `docs/ja/` mirrors, alongside `interrupts` and
`systemAlertHandling`, extending BE-0314's existing comparison of when to reach for each mechanism.

### Unit 7 — tests

Schema parse/validate for the new toggle; a fake driver whose presence query flips between polls; the
guard dismissing the banner before a step's own actuation; the dismissal reaching the step's
`AlertEvent`s and carrying the discriminator that tells it apart from an alert dismissal; the
capability gate leaving a backend without it unchanged; the config-then-scenario
precedence layering; and, if Unit 1 finds the interruption-monitor path is needed, coverage for that
path the way BE-0399's own test suite covers the alert monitor.

### Prime directives preserved

- **AI never judges.** The presence query and the swipe-dismiss action are both deterministic driver
  calls; this item adds no new AI surface.
- **Determinism first.** No fixed sleep: the guard polls on a bounded interval and dismisses the
  banner by its measured frame, never by waiting out the banner's own auto-dismiss timeout.
- **App-agnostic.** The toggle and the guard are generic runner mechanisms; no per-app code is added.

## Alternatives considered

- **Route the banner through `interrupts`.** Rejected on the same premise BE-0315's motivation
  established for a system alert: a process outside the application under test draws the banner, so
  `interrupts`' condition — evaluated only against the application's own tree — has nothing to check
  against.
- **Dismiss the banner with a tap instead of a swipe.** Rejected: tapping a real banner opens the
  notification's own app, which would navigate the run away from the scenario under test, the opposite
  of clearing the banner. A swipe is the gesture that removes it without that side effect.
- **Add an AI-vision fallback for a case the native query cannot resolve, mirroring the vision guard
  system alerts once had.** Rejected under prime directive 1. BE-0402 already removed the equivalent
  fallback from `run`'s system-alert path for the same reason: the banner's presence and frame are
  exactly the kind of fact a native query answers, with no judgment call for a model to make.
- **Let the banner auto-dismiss on its own timeout instead of swiping it away.** Rejected under prime
  directive 2 (no fixed sleep), and a banner that has not yet auto-dismissed is exactly the window in
  which it interferes with a tap.

## Progress

> Keep this current as work proceeds. The checklist mirrors the MECE work breakdown in
> *Detailed design* (one box per unit of work); the log records what changed and when
> (oldest first), linking the PRs.

- [ ] Unit 1 — measure the banner's accessibility surface on a booted Simulator across the covered
      iOS versions.
- [ ] Unit 2 — deterministic presence query (`Driver` method reporting the banner's frame or absence).
- [ ] Unit 3 — deterministic swipe-dismiss action anchored to the measured frame.
- [ ] Unit 4 — reactive guard wiring behind a config/scenario toggle, following the existing
      precedence.
- [ ] Unit 5 — showcase fixture, including the app-side foreground banner presentation and a tap
      target inside the banner's frame, and on-device verification.
- [ ] Unit 6 — docs (`docs/scenarios.md` + ja).
- [ ] Unit 7 — tests.
- [ ] Follow-up — close the poll-and-clear fallback's residual race window, once Unit 1's measurement
      settles which path Unit 4 takes.

## References

- [BE-0314](../BE-0314-scenario-interrupt-handlers/BE-0314-scenario-interrupt-handlers.md) — the
  `interrupts` field, and why its in-tree condition cannot reach a system-owned overlay.
- [BE-0315](../BE-0315-ios-native-system-alert-handling/BE-0315-ios-native-system-alert-handling.md) —
  the native presence-query and reactive-guard shape this proposal reuses for a banner instead of an
  alert.
- [BE-0399](../BE-0399-ios-system-alert-interruption-policy/BE-0399-ios-system-alert-interruption-policy.md) —
  the interruption monitor and its ordering, which Unit 1 must measure against the banner before
  Unit 4 can reuse it.
- [BE-0406](../BE-0406-system-alert-declared-prompts/BE-0406-system-alert-declared-prompts.md) — the
  per-prompt declaration this item's single config toggle is simpler than, since a banner has no
  distinct prompts to declare.
- [BE-0177](../BE-0177-run-behavior-target-config/BE-0177-run-behavior-target-config.md) — the
  config-then-scenario, flag-overridable precedence Unit 4's toggle follows.
- [`docs/scenarios.md`](../../docs/scenarios.md) — the existing `swipe` step whose coordinate machinery
  Unit 3 reuses, and the `push` step Unit 5's fixture uses to raise the banner deterministically.
- Apple, [`XCTestCase.addUIInterruptionMonitor(withDescription:handler:)`](https://developer.apple.com/documentation/xctest/xctestcase/adduiinterruptionmonitor(withdescription:handler:)) —
  the monitor Unit 4's interruption path would reuse, cited in BE-0314 and BE-0399 as the same prior
  art.
