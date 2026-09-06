**English** · [日本語](BE-XXXX-device-appearance-connectivity-state-ja.md)

# BE-XXXX — Device state steps: orientation, appearance, and airplane mode

<!-- BE-METADATA -->
| Field | Value |
|---|---|
| Proposal | [BE-XXXX](BE-XXXX-device-appearance-connectivity-state.md) |
| Author | [@0x0c](https://github.com/0x0c) |
| Status | **Proposal** |
| Tracking issue | [Search](https://github.com/bajutsu-e2e/bajutsu/issues?q=is%3Aissue+label%3Aroadmap-tracking+in%3Atitle+"BE-XXXX") |
| Topic | Scenario authoring features |
| Related | [BE-0035](../BE-0035-device-control-primitives/BE-0035-device-control-primitives.md), [BE-0052](../BE-0052-device-state-timezone-clipboard-shake/BE-0052-device-state-timezone-clipboard-shake.md), [BE-0212](../BE-0212-granular-device-control-capabilities/BE-0212-granular-device-control-capabilities.md), [BE-0128](../BE-0128-device-step-capability-preflight/BE-0128-device-step-capability-preflight.md), [BE-0029](../BE-0029-visual-regression-assertions/BE-0029-visual-regression-assertions.md), [BE-0171](../BE-0171-element-scoped-visual-assertions/BE-0171-element-scoped-visual-assertions.md), [BE-0282](../BE-0282-real-backend-network-coverage/BE-0282-real-backend-network-coverage.md) |
<!-- /BE-METADATA -->

## Introduction

Three device-state steps, proposed together because they are one shape: `setOrientation`,
`setAppearance`, and `setAirplaneMode`. Each mutates the device outside the element tree, each is
gated by its own `deviceControl.*` capability token
([BE-0212](../BE-0212-granular-device-control-capabilities/BE-0212-granular-device-control-capabilities.md)),
and each is honored by whichever channel is faithful on a given backend. The support matrix is
deliberately uneven, and the unevenness is the point: the iOS Simulator has no radio, so it
advertises no airplane-mode token and preflight refuses such a scenario before any device work.

## Motivation

A suite that must verify a landscape layout, a dark theme, or offline behaviour cannot express the
state change today, so all three flows are absent from every scenario in this repository.

Dark mode is the load-bearing one. Visual regression
([BE-0029](../BE-0029-visual-regression-assertions/BE-0029-visual-regression-assertions.md)) with
element scoping and masking
([BE-0171](../BE-0171-element-scoped-visual-assertions/BE-0171-element-scoped-visual-assertions.md))
is one of the tool's strongest guarantees, and it can only ever compare one appearance, because
nothing can put the device into the other. Airplane mode is the missing half of offline testing:
scenario `mocks` already stub a *response*
([BE-0282](../BE-0282-real-backend-network-coverage/BE-0282-real-backend-network-coverage.md)), but
no step severs the radio, so an application's own reachability and retry paths never run under test.

Orientation completes the set. It is the state change with the widest layout blast radius, and the
one an application is most likely to get wrong without ever being asked about it.

Once this ships, a reader can point at a baseline pair. The repository holds no visual baseline for a
second appearance today, because no scenario can reach one. After this change a **single** scenario
file with two `data` rows produces two comparisons, against `home-light.png` and `home-dark.png`, and
that pair sits in the showcase baselines directory. No new assertion kind is needed to get there — see
below.

## Detailed design

### The three actions

```ebnf
Action ::= …
  | { setOrientation:  { to: "portrait" | "landscape" } }
  | { setAppearance:   { to: "light" | "dark" } }
  | { setAirplaneMode: { enabled: boolean } }
```

`to:` reads the way the sentence does and matches the existing single-payload device steps
(`setClipboard: { text }`, `setLocation: { lat, lon }`). The orientation vocabulary is two values
rather than four on purpose: `landscapeLeft` and `landscapeRight` have no faithful web equivalent and
no author-visible difference on a phone-shaped target, so this item ships the portable pair and
records the four-value question below.

### Three new capability tokens

`deviceControl.orientation`, `deviceControl.appearance`, and `deviceControl.airplaneMode` join
`base.Capability` beside `DC_SET_LOCATION`, `DC_CLIPBOARD`, `DC_PUSH`, `DC_CLEAR_KEYCHAIN`,
`DC_APP_LIFECYCLE`, and `DC_STATUS_BAR` (`bajutsu/common/drivers/base.py:88-93`). Each gains a row in
`_DEVICE_CONTROL_OPS` (`capability_preflight.py:163`), which is a data table of token, label, and
predicate — so the preflight itself needs no new logic.

One edit here is small and easy to miss. `DEVICE_CONTROL_ALL` (`base.py:127`) is how the xcuitest
driver advertises the whole family in one shot (`xcuitest.py:840`). That shortcut **must be broken**
for airplane mode, since the Simulator cannot honor it. Either xcuitest lists its subset explicitly,
or `DEVICE_CONTROL_ALL` is redefined as the operations a full simctl-backed device honors, with
airplane mode outside it.

### The support matrix, stated honestly

| token | xcuitest | adb | playwright | fake |
|---|---|---|---|---|
| `deviceControl.orientation` | ✅ through the resident runner, not `simctl` | ✅ disable accelerometer rotation, then set `user_rotation` | ✅ viewport swap on the context | — |
| `deviceControl.appearance` | ✅ `simctl ui <udid> appearance light\|dark` | ✅ `cmd uimode night yes\|no` | ✅ the context's `color_scheme` emulation | — |
| `deviceControl.airplaneMode` | **—** the Simulator has no radio | ✅ `cmd connectivity airplane-mode enable\|disable` | ✅ the context's offline switch | — |

Two rows in that table drive the design, and neither should be smoothed over.

**iOS orientation is not a `simctl` operation.** `xcrun simctl` has no orientation subcommand;
interface orientation on the Simulator is set through `XCUIDevice.shared.orientation`, which lives in
the resident XCUITest runner — the same place `handleSystemAlert` and the picker-wheel support live.
Rather than mint a fourth top-level token, the scenario-facing concept stays in the device-state
family, since it *is* a device mutation outside the element tree, and the iOS controller reaches the
runner. Mechanically, `Environment.controller(self, eff)`
(`bajutsu/common/platform_lifecycle/protocols.py:272`) widens to take the started driver, matching
`relauncher(self, eff, scenario, driver)` (`protocols.py:262`) which already does.

**The iOS Simulator cannot honor airplane mode at all.** There is no radio, no `simctl` surface, and
`overrideStatusBar`'s bars are cosmetic. So `xcuitest` advertises no airplane-mode token, and
preflight refuses such a scenario before any device work, with a message naming the alternative —
scenario `mocks` plus a `network` filter, which on iOS is the only offline path there is. Advertising
nothing and failing early is what
[BE-0212](../BE-0212-granular-device-control-capabilities/BE-0212-granular-device-control-capabilities.md)'s
per-operation split exists to make expressible.

### The web backend gets a `DeviceControl` for the first time

`WebEnvironment.controller` returns `None` today, with the comment *"the driver owns the browser; no
simctl device control"* (`environments/web.py:105-106`). A new `web_device_control(driver)` factory
returns a control bound to the live driver, honoring the three new operations and raising
`UnsupportedAction` for the rest of the protocol — the shape the Android controller already uses.
Preflight gates the rest away up front, so that raise is a backstop rather than a silent no-op. This
is the largest structural change in the item, and its own work unit.

### Three demarcations, written out because each is a trap

- **The `rotate` action is not `setOrientation`.** `rotate: { sel, radians }` is a two-finger gesture
  that rotates content *inside* an element — a map, a photo — behind the `multiTouch` capability
  ([BE-0232](../BE-0232-adb-multitouch-gestures/BE-0232-adb-multitouch-gestures.md)).
  `setOrientation` changes the device's interface orientation and re-lays-out the whole application,
  behind a device-control token, through an entirely different channel. One English word, no shared
  code.
- **The `serve` theme system is not `setAppearance`.**
  [BE-0191](../BE-0191-pluggable-theme-system-serve-ui/BE-0191-pluggable-theme-system-serve-ui.md) is
  the Bajutsu Web UI's own light and dark theme, the operator's browser chrome. `setAppearance` sets
  the appearance of the application under test, on the device. There is no overlap.
- **`overrideStatusBar`'s bars are not connectivity.** `wifiBars` and `cellularBars`
  ([BE-0035](../BE-0035-device-control-primitives/BE-0035-device-control-primitives.md)) paint the
  simulator status bar so a screenshot is stable. The radio is untouched, and the application's own
  requests still succeed. Reaching for `wifiBars: 0` to test offline behaviour is the obvious
  mistake, and it produces a scenario that asserts an offline banner and never sees one.

### No new assertion kind for appearance

An appearance assertion would read the device setting. Immediately after `setAppearance` that is
nearly a tautology, and it says nothing about whether the application followed. The claim an author
actually wants is "this screen renders its dark theme", and the grammar reaches it two ways already:
a `visual` assertion against a per-appearance baseline, element-scoped since BE-0171, or an ordinary
`exists` / `selected` / `label` assertion on whatever the theme changes.

Adding one would also be the only assertion in the grammar resolving against neither the element tree
nor the network, the two axes [selectors](../../docs/selectors.md) documents. The cross-appearance
matrix then falls out of composition, with no new grammar at all:

```yaml
- name: home renders in both appearances
  data: [{ appearance: light }, { appearance: dark }]
  before:
    - setAppearance: { to: "${row.appearance}" }
  steps:
    - wait: { for: { id: home.title }, timeout: 5 }
  expect:
    - visual: { baseline: "home-${row.appearance}.png", element: { id: home.card } }
```

Data expansion interpolates `${row.*}` across the whole scenario
([BE-0031](../BE-0031-data-driven-scenarios/BE-0031-data-driven-scenarios.md)), so both the step
payload and the baseline filename are covered today. One file, two baselines, no new mechanism.

### Settling without a fixed sleep

Orientation and appearance change the layout, so the next `query()` may still show the old tree. The
handler does **not** sleep. It performs the mutation, then polls the device's own read-back to a
bounded deadline on the existing deadline-and-backoff skeleton the condition waits already share.
`simctl ui <udid> appearance` with no argument prints the current value, `cmd uimode night` prints it
on Android, and the browser context answers directly.

The limit is stated the way `scroll` states its physics: the handler waits for **the device** to
report the new state. Whether the **application** has finished re-laying-out is the author's
business, waited for with an ordinary `wait: { for: … }`. Nothing here is a settle-sleep in disguise.

### Work breakdown (MECE)

1. **Grammar and tokens.** Three actions, three `Capability` members, the `DEVICE_CONTROL_ALL`
   correction, three `_DEVICE_CONTROL_OPS` rows, and the DSL grammar with its Japanese mirror.
2. **Protocol widening.** The three `DeviceControl` methods, and `controller(eff)` widened to
   `controller(eff, driver)` across `protocols.py` and every environment, with its single call site.
3. **iOS.** `simctl ui appearance` set and read-back; orientation routed through the resident runner
   with its channel message; airplane mode deliberately unadvertised, with the preflight message
   naming `mocks`.
4. **Android.** The three `adb` command builders and read-backs, including disabling accelerometer
   rotation before setting `user_rotation`.
5. **Web.** The `web_device_control(driver)` factory, `WebEnvironment.controller` returning it, and
   the three operations on the Playwright driver.
6. **Settle condition.** The bounded read-back poll, with the "device settled, application not
   necessarily" limit documented.
7. **Documentation and fixtures.** The [drivers](../../docs/drivers.md) capability table,
   [scenarios](../../docs/scenarios.md), the three demarcations above, and the two-row
   cross-appearance showcase scenario with its baseline pair.
8. **On-device validation.** One scenario each in the iOS, Android, and web end-to-end workflows.

### Prime directives preserved

- **No LLM on the run path.** Every operation is a command to a device and a read-back of its
  answer. The verdict still comes from machine-checkable assertions.
- **Determinism.** No fixed sleep: the settle is a bounded poll on the device's own reported state,
  and a backend that cannot honor an operation fails at preflight rather than partway through.
- **App-agnostic.** The steps are identical across targets, and the per-backend difference lives in
  the capability set and the chosen channel, which is where a platform difference belongs.
- **Codegen.** These are device-level mutations with no in-app equivalent, so codegen emits a
  labeled `TODO`, matching how it already treats the BE-0035 device-control steps.

## Alternatives considered

- **Add an `appearance` assertion kind.** Rejected: it reads the device setting, which after
  `setAppearance` is nearly tautological and says nothing about the application; it would be the
  grammar's only assertion resolving against neither the element tree nor the network; and the claim
  authors want is already expressible with `visual` plus a per-appearance baseline. The read-back it
  would have used is kept, as the runner's settle condition.
- **Approximate each state from inside the application**, through a launch environment variable or a
  deeplink such as `UI_TEST_FORCE_DARK=1`. Rejected on the grounds BE-0035 already used: it works per
  application and breaks app-agnosticism, so the tool would behave differently depending on which
  hooks a target happens to expose. Launch environment stays available for genuinely app-specific
  setup.
- **Advertise `deviceControl.airplaneMode` on iOS and implement it as `overrideStatusBar` with zero
  bars.** Rejected outright. The bars are cosmetic and the application's traffic still succeeds, so a
  scenario asserting "shows the offline banner" fails confusingly — and one asserting "the request
  was not made" passes for entirely the wrong reason. Advertising nothing and failing at preflight is
  strictly more honest.
- **Three separate roadmap items, one per state.** Rejected: all three are the same shape, and two of
  the eight work units — widening the `DeviceControl` protocol, and giving the web backend a
  controller at all — are shared. Splitting would triple the protocol churn for no gain in review
  clarity.

## Progress

> Keep this current as work proceeds. The checklist mirrors the MECE work breakdown in
> *Detailed design* (one box per unit of work); the log records what changed and when
> (oldest first), linking the PRs.

- [ ] Grammar and tokens, including the `DEVICE_CONTROL_ALL` correction.
- [ ] `DeviceControl` protocol methods and the `controller(eff, driver)` widening.
- [ ] iOS — appearance through simctl, orientation through the resident runner, airplane mode refused
      at preflight.
- [ ] Android — the three `adb` builders and read-backs.
- [ ] Web — a `DeviceControl` for the first time, and the three operations.
- [ ] Settle condition — the bounded read-back poll and its documented limit.
- [ ] Documentation, the three demarcations, and the cross-appearance showcase scenario.
- [ ] On-device validation in the three end-to-end workflows.

Open questions to settle while building:

- The four-value orientation vocabulary. Shipped as two; whether iOS-only authors need
  `landscapeLeft` and `landscapeRight` is unresolved.
- Whether a real iOS device could ever honor airplane mode. A physical device's toggle is not
  reachable from `xcodebuild`, so the answer is probably still no, but it should be stated rather
  than assumed.
- Interaction with parallel workers. Device control is already per-lane, but a web lane's offline
  switch is context-scoped while an Android emulator's airplane mode is device-global, so two lanes
  sharing one emulator would interfere. The likely answer is to refuse airplane mode on Android when
  lanes share a serial.
- Whether the device state should be recorded per scenario in the manifest, so a `visual` diff
  against the wrong-appearance baseline is diagnosable from evidence alone.
- Whether `erase` resets appearance and orientation on each backend. If it does not, a scenario that
  sets dark mode leaks into the next scenario in the same lease, which would be a determinism defect.
  This needs pinning by test.

## References

- [BE-0035 — Device-control steps](../BE-0035-device-control-primitives/BE-0035-device-control-primitives.md)
  — the step pattern this follows, and the `overrideStatusBar` bars it must be distinguished from.
- [BE-0052 — Device-state primitives: timezone, clipboard, shake](../BE-0052-device-state-timezone-clipboard-shake/BE-0052-device-state-timezone-clipboard-shake.md)
  — the second device-state slice this continues.
- [BE-0212 — Split the coarse deviceControl capability into per-operation tokens](../BE-0212-granular-device-control-capabilities/BE-0212-granular-device-control-capabilities.md)
  and [BE-0128 — Preflight-gate device-control steps by capability](../BE-0128-device-step-capability-preflight/BE-0128-device-step-capability-preflight.md)
  — the token split and the gate that make an uneven support matrix expressible.
- [BE-0029 — Visual-regression assertions](../BE-0029-visual-regression-assertions/BE-0029-visual-regression-assertions.md)
  and [BE-0171 — Element-scoped visual assertions](../BE-0171-element-scoped-visual-assertions/BE-0171-element-scoped-visual-assertions.md)
  — what a second appearance unlocks.
- [BE-0282 — Real-backend network capture, mock, and assertion coverage in CI](../BE-0282-real-backend-network-coverage/BE-0282-real-backend-network-coverage.md)
  — the response-stubbing half of offline testing, and the iOS alternative preflight names.
- `bajutsu/common/drivers/base.py:88-141` (the `deviceControl.*` tokens and `DEVICE_CONTROL_ALL`),
  `bajutsu/common/capability/capability_preflight.py:163` (`_DEVICE_CONTROL_OPS`),
  `bajutsu/common/platform_lifecycle/protocols.py:262-272` (`relauncher` and `controller`),
  `bajutsu/common/platform_lifecycle/environments/web.py:105` (the `None` this item replaces).
