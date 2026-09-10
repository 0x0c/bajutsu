**English** · [日本語](BE-XXXX-ios-notification-banner-swipe-dismiss-ja.md)

# BE-XXXX — Swipe away an interrupting iOS notification banner reactively

<!-- BE-METADATA -->
| Field | Value |
|---|---|
| Proposal | [BE-XXXX](BE-XXXX-ios-notification-banner-swipe-dismiss.md) |
| Author | [@0x0c](https://github.com/0x0c) |
| Status | **Proposal** |
| Tracking issue | [Search](https://github.com/bajutsu-e2e/bajutsu/issues?q=is%3Aissue+label%3Aroadmap-tracking+in%3Atitle+"BE-XXXX") |
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
element a step is about to tap. The banner has no fixed trigger a scenario can place a check after:
a push notification's arrival depends on a server, and even a local notification an app schedules for
itself lands relative to wall-clock time, not relative to any step. A step whose target happens to sit
under the banner's frame can therefore tap the banner instead of the target, or resolve against
whichever element XCUITest's own hit-testing picks once the overlap is present — a defect that reads
as flakiness, since nothing in the run's report records that a banner ever appeared.

The gap is structural, not incidental. A process outside the application under test draws the banner,
the same separation BE-0315's motivation measured for a SpringBoard alert, so the `interrupts` field's
condition — evaluated only against the application's own tree — has nothing to check against. And the
banner carries no button: the deterministic dismiss BE-0315 built for a system alert resolves a button
by its label, but a person clears a real banner with an upward swipe, not a tap, and tapping it instead
opens the notification's own app and navigates the run away from the scenario it was running. The
gesture this proposal needs already exists in Bajutsu — `swipe` (documented in
[`docs/scenarios.md`](../../docs/scenarios.md) in both a directional and a coordinate form) — but no
existing mechanism knows where the banner is or when to reach for it.

A later reader can tell whether this proposal arrived by running a scenario that arms a local
notification to go off mid-flow, timed so the banner's measured frame overlaps the scenario's next tap
target. Before this proposal, that tap is unreliable: where it lands depends on how the two frames
overlap at the moment XCUITest resolves it. After this proposal, the banner clears itself before the
tap executes, and the tap lands on the target every time.

## Detailed design

### Unit 1 — measure the banner's accessibility surface on a device

Before any driver method is added, measure how a foreground notification banner actually appears to
XCUITest, on a booted Simulator, across the iOS versions the existing system-alert work already covers
(18.6, 26.3, 26.4, 26.5). Three facts decide the shape of every later unit: which process's element
tree exposes the banner — SpringBoard, as with a system alert, or a distinct process; what frame or
identifier it offers, if any; and whether an ordinary `tap`/`type` step already receives XCUITest's own
interruption-monitor treatment when its target sits under the banner's frame, the treatment BE-0399
measured for a system alert, or whether hit-testing instead resolves the overlap silently, with no
interruption dispatched at all. This unit produces no code; the measurement fixes the design questions
units 2 through 4 currently leave open.

### Unit 2 — a deterministic presence query

Add a driver method that reports whether a notification banner is currently showing and, when one is,
the on-screen frame the swipe in Unit 3 needs. This mirrors the shape of BE-0315's
`system_alert_labels()`: a thin, non-blocking read that reports a fact and decides nothing.

### Unit 3 — a deterministic swipe-dismiss action

Add a driver action that swipes the banner away, anchored to the frame Unit 2 reports rather than a
fixed screen coordinate, so the gesture holds across device sizes. The direction matches how a person
dismisses a real banner: upward, off the top of the screen. The action reuses the coordinate machinery
`swipe`'s existing driver implementation already has, rather than adding a second gesture primitive.

### Unit 4 — reactive wiring

A config- and scenario-level toggle arms a guard that polls Unit 2's presence query on the bounded
interval BE-0315 already established for the SpringBoard probe, and dismisses the banner through
Unit 3's action the moment one is found. When Unit 1 finds that XCUITest's own interruption monitor
treats an overlapping banner the way it treats a system alert, the guard answers through that monitor
too, mirroring how BE-0399's monitor answers an interrupting alert. When Unit 1 finds otherwise, a
poll-and-clear immediately before each act step's own actuation is the fallback. The toggle follows the
same config-then-scenario, flag-overridable precedence
([BE-0177](../BE-0177-run-behavior-target-config/BE-0177-run-behavior-target-config.md)) `dismissAlerts`
already established.

### Unit 5 — showcase fixture and on-device verification

Add a showcase scenario that arms a local notification to go off mid-flow, timed so the banner's measured
frame overlaps the scenario's next tap target, and assert that the tap still lands on that target. The
off-Simulator gate cannot prove a native swipe against a real banner; the unit that lands the driver
methods must exercise this scenario on a booted Simulator.

### Unit 6 — docs

Document the new toggle in [`docs/scenarios.md`](../../docs/scenarios.md) and its `docs/ja/` mirror,
alongside `interrupts` and `dismissAlerts`/`systemAlertHandling`, extending BE-0314's existing
comparison of when to reach for each mechanism.

### Unit 7 — tests

Schema parse/validate for the new toggle; a fake driver whose presence query flips between polls; the
guard dismissing the banner before a step's own actuation; the config-then-scenario precedence
layering; and, if Unit 1 finds the interruption-monitor path is needed, coverage for that path the way
BE-0399's own test suite covers the alert monitor.

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
- [ ] Unit 5 — showcase fixture and on-device verification.
- [ ] Unit 6 — docs (`docs/scenarios.md` + ja).
- [ ] Unit 7 — tests.

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
  Unit 3 reuses.
- Apple, [`XCTestCase.addUIInterruptionMonitor(withDescription:handler:)`](https://developer.apple.com/documentation/xctest/xctestcase/adduiinterruptionmonitor(withdescription:handler:)) —
  the monitor Unit 4's interruption path would reuse, cited in BE-0314 and BE-0399 as the same prior
  art.
