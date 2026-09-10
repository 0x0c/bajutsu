**English** · [日本語](BE-0415-driver-call-trace-per-scenario-ja.md)

# BE-0415 — Trace Python↔driver calls per scenario, permanently

<!-- BE-METADATA -->
| Field | Value |
|---|---|
| Proposal | [BE-0415](BE-0415-driver-call-trace-per-scenario.md) |
| Author | [@0x0c](https://github.com/0x0c) |
| Status | **Implemented** |
| Tracking issue | [Search](https://github.com/bajutsu-e2e/bajutsu/issues?q=is%3Aissue+label%3Aroadmap-tracking+in%3Atitle+"BE-0415") |
| Topic | Driver & backend architecture |
| Related | [BE-0407](../BE-0407-step-latency-driver-internal-tuning/BE-0407-step-latency-driver-internal-tuning.md) |
<!-- /BE-METADATA -->

## Introduction

[BE-0407](../BE-0407-step-latency-driver-internal-tuning/BE-0407-step-latency-driver-internal-tuning.md)
measured why a `tap` step is slow on the iOS Simulator and the Android emulator by running
[`trace_run.py`](../BE-0407-step-latency-driver-internal-tuning/misc/step-performance/trace_run.py),
a standalone wrapper script that monkey-patches the driver classes, the transport functions, and
`subprocess.run` before starting `bajutsu run`, then writes every timed call to one JSON file for the
whole invocation. It answered that item's question, but it only exists as a script someone has to
remember to run instead of `bajutsu run` itself, and its output is not scoped to a scenario — a
multi-scenario run interleaves every scenario's calls into one flat list.

This item makes the same kind of measurement a permanent, opt-in feature of `bajutsu run`: pass
`--trace-driver` and every run writes one `driver_trace.json` per scenario, next to that scenario's
other evidence, recording every Python↔driver call — the driver method invoked, how many
host-device round trips it took, and (on Android) which of those round trips fell back to a
subprocess — with a start time and an elapsed duration, attributed to the step it happened during.
Unlike `trace_run.py`, none of this is monkey-patched: it composes at dependency-injection points the
orchestrator already has — mostly built for testing (BE-0143) or for BE-0407's own drain-tracking
wrapper — plus one small thread-local trace context this item adds for step correlation.

### Not doing

- **The web backend (Playwright) is out of scope.** It is not a "simulator or emulator" in the sense
  this item's motivation names, and network-layer communication with the browser is internal to
  Playwright's own Python binding, not something bajutsu's driver code initiates the way it does the
  XCUITest and adb round trips.
- **Screenshot / element-tree evidence-write timing (`FileSink.capture`) is out of scope.** The
  driver calls it makes internally (`screenshot()`, `query()`) are already visible under the
  `driver` category; what evidence writing adds on top is file I/O and redaction overhead, which is
  not "operating the simulator or emulator" — the motivation this item exists for.
- **Nothing here changes a scenario's pass/fail.** The trace file is diagnostic evidence only,
  exactly like `--score` and `--zip` today; prime directive 1 keeps every AI and every diagnostic
  off the verdict path, and this item introduces neither.
- **A `transport` record's `response` field is a small structured outcome, never the full reply
  body.** A GET (a read) carries none at all; a POST carries only `_Reply.status` (iOS) or
  `ActOutcome.acted` / `.published_mark` (Android). The element tree an `/elements` or `/act`
  reply can carry stays out — that content is already the run's own evidence (`elements.json`), and
  duplicating it into every scenario's trace file would make the diagnostic artifact as large as, or
  larger than, the run it is diagnosing.

## Motivation

BE-0407 already cut a meaningful share of step latency, but its own numbers (0.3–0.6 s per iOS tap
step, 0.6–1.2 s per Android tap step) are still short of the 250–500 ms target, and closing the rest
needs a larger, device-side executor change tracked separately
([BE-0408](../BE-0408-step-latency-device-executor-protocol/BE-0408-step-latency-device-executor-protocol.md)–[BE-0410](../BE-0410-step-latency-android-device-executor/BE-0410-step-latency-android-device-executor.md)).
Whoever picks up that work — or investigates the next scenario that regresses in wall time — needs
the same per-call breakdown BE-0407's investigation used, but today that means finding
`trace_run.py` inside a roadmap item's `misc/` directory, remembering its invocation is `bajutsu`'s
own argument list with an extra wrapper in front, and manually splitting its one combined JSON file
by scenario. Every one of those is friction a permanent CLI flag removes.

The cost of leaving it as a one-off script is not hypothetical: BE-0407 itself is not the last word
on driver-internal latency (its own Introduction says so), and any future investigation — a
regression a contributor notices in CI, a new backend's first performance pass — starts from zero
without this. Building the capability once, correctly scoped to a scenario and integrated with the
run directory a `run` already writes, means the next investigation runs `bajutsu run --trace-driver`
against the suite that actually reproduces the problem, no separate script, no manual correlation of
which timed call belongs to which scenario.

## Detailed design

### Categories measured

Three categories, matching what actually varies host-device round trips within one step:

- **`driver`** — one record per `Driver` protocol method call (`tap`, `query`, `screenshot`, `wait_for`,
  …), plus two capability-protocol methods `trace_run.py` also measured — `drain_interruptions` and
  `settled_query`, present only on a driver that opts into the matching capability protocol (below) —
  that the orchestrator calls directly on a concrete driver.
- **`transport`** — one record per host-device round trip *inside* a single driver method call. A
  `query()` call that also fetches `/zorder` produces two `transport` records under one `driver`
  record; a `tap()` call that resolves cleanly produces one. A record for a POST round trip (an
  actuation, not a read) additionally carries the small structured outcome the device already
  returns — iOS's `_Reply.status` (`bajutsu/common/drivers/xcuitest/_reply.py:22`, e.g. `"ok"` /
  `"stale"`) or Android's `ActOutcome.acted` / `.published_mark`
  (`bajutsu/common/drivers/adb/act_outcome.py:25-26`) — never the full response body: `_Reply.raw`
  and the tree an `act()` reply can carry (`want_tree`) stay out, so a trace stays a small,
  per-call log rather than a second copy of the run's own evidence capture.
- **`subprocess`** — Android only. A `uiautomator dump` fallback
  ([`bajutsu/common/drivers/adb/adb_driver.py:457`](../../bajutsu/common/drivers/adb/adb_driver.py))
  or an `adb shell` probe (`id_u`, `getevent`, `wm size`) issued through the same seam
  (`adb_driver.py:1148,1159,1190`). iOS's `simctl`/`xcodebuild` process spawns happen once at device
  lease, before any scenario's steps run, so they carry no per-step signal and are not measured.

Every record carries `{category, step, name, started_at, elapsed_s}`: `step` is the step index and
kind (`f"{i:02d}:{kind}"`, matching `trace_run.py`'s own key) the call happened during, `started_at`
is a wall-clock Unix timestamp (so a record can be cross-referenced against `device.log` or the
step's own `started_at` in `manifest.json`), and `elapsed_s` is the call's own duration. A
`transport` record for a POST round trip carries one further field, `response` — the small
structured outcome described above — that a GET (a read) never carries.

### Composition over monkey-patching

`trace_run.py` has to monkey-patch, because it is an external script that cannot edit
`bajutsu`'s own source. This item can, and the orchestrator already exposes the seams a permanent
version of the same measurement needs — none of them new, all added for testability or by BE-0407
itself:

1. **`TracingDriver`** (new) — a `base.Driver`-conforming delegating proxy that implements
   **only** `__getattr__`: it declares no protocol methods of its own. Looking up an attribute
   checks whether the wrapped driver actually has it (a plain `getattr`, which raises exactly as
   the unwrapped driver would when it does not) and, for a name on the traced list, returns a
   timed wrapper instead of the bare attribute; everything else passes through unchanged. This
   matters beyond `tap`/`query`/`screenshot`: `drain_interruptions` and `settled_query` are not
   extra, driver-specific methods — they belong to the `@runtime_checkable` capability protocols
   `base.InterruptionPolicyTarget` and `base.SettledReadProvider`
   ([`bajutsu/common/drivers/base/`](../../bajutsu/common/drivers/base/)), which the orchestrator
   probes with `isinstance`, not `hasattr`
   (`gestures.py:212`, `waits/_functions.py:273`, `loop/_step_runner.py:166`). A proxy that declared
   those two as real methods would answer `isinstance` `True` for every driver it wraps, including
   `FakeDriver` (no `settled_query`) and `PlaywrightDriver` (neither) — sending both down a branch
   that then fails inside the proxy's own `__getattr__`. Because `TracingDriver` declares nothing of
   its own, `isinstance` against any capability protocol reads the wrapped driver's real capability
   set, unchanged.
2. **A shared trace context, not a threaded parameter** — the driver the steps run against is built
   several calls below anywhere `--trace-driver` is visible (see unit 5), and the alternative —
   adding a parameter to `backends.make_driver` and threading it through `launch_driver`,
   `RunEnvironment`, and every concrete environment's constructor — touches every backend's
   lifecycle class for a diagnostic feature. Instead, `make_driver` and `AdbDriver`'s subprocess path
   (unit 4) consult the same per-thread trace context unit 6 already needs for step correlation: a
   thread-local, set once by `_ScenarioRunner.run_one` when `--trace-driver` is on. Reading ambient
   state from a thread-local is a smaller, more contained change than adding a constructor parameter
   to every `RunEnvironment` subclass, at the cost of the seam being implicit rather than an explicit
   argument — see *Alternatives considered*.
3. **`transport` on iOS** —
   [`XcuitestDriver.__init__`](../../bajutsu/common/drivers/xcuitest/xcuitest_driver.py) already
   wraps its own `self._transport` in a delegating closure, `_tracking_transport`, to fold
   BE-0407 Unit 6's drain-tracking in. This item adds one more optional constructor argument (e.g.
   `on_transport_call: Callable[[str, float, float, str | None], None] | None`, the last argument
   being `_Reply.status` on a POST, `None` on a GET), applied as a second wrap in the same place.
   `backends.make_driver`'s `xcuitest` branch passes it whenever unit 2's trace context says tracing
   is on — no change to `_raw_http_transport` or any other module.
4. **`transport` and `subprocess` on Android, both through the same seam** —
   [`backends.make_driver`](../../bajutsu/common/backends.py)'s `adb` branch already receives
   `fetch_hierarchy` / `fetch_clock` / `act` as plain callables from its caller and forwards them to
   `AdbDriver(...)` unchanged; when tracing is on it wraps each of the three (`transport`), and
   `act`'s wrap also reads the `ActOutcome` it returns (`.acted`, `.published_mark`) into the
   record — the one Android round trip that is itself a POST. The same branch does the same for
   `subprocess`: `AdbDriver.__init__` already takes
   `run: RunFn = adb.real_run` ([`adb_driver.py:125`](../../bajutsu/common/drivers/adb/adb_driver.py)),
   and every adb subprocess call it issues goes through `self._run` — the `uiautomator dump`
   fallback (`:457`), the `id_u`/`getevent`/`wm size` probes (`:1148,1159,1190`), and
   `adb.Env(self.serial, run=self._run)` (`:1400,1453`). `make_driver` passes a timed wrap of
   `adb.real_run` as `run=` under the same condition, so neither category needs a monkey-patch of
   `subprocess` in any module. The one call this seam does not reach, `AdbDriver._run_text`
   (`:1381`, the `typeText` path, kept off `self._run` so a typed secret never reaches the adb
   process's argv), is already "routed through a class-level attribute so tests can patch it" by its
   own comment; the module substitutes that one attribute the same way, under the same condition.
5. **The `driver`-category wrap, at the seam that actually builds the scenario's driver** — the
   scenario's driver does **not** come from `device_pool`'s injectable `make_driver` argument
   (`Callable[..., base.Driver] = _make_driver`): that parameter is read exactly once
   ([`pool.py:387`](../../bajutsu/common/runner/pool.py)), for the read-only network-evidence
   provider (BE-0020) a run falls back to when its own actuator does not observe network via the
   driver — it never builds the driver a scenario's steps run against. That driver comes from
   `launch_driver(...)` ([`pool.py:408`](../../bajutsu/common/runner/pool.py)), which calls
   `RunEnvironment.start(...)`; each environment then calls `backends.make_driver` itself
   ([`xcuitest_environment.py:772`](../../bajutsu/common/platform_lifecycle/environments/xcuitest/xcuitest_environment.py),
   [`android_environment.py:166`](../../bajutsu/common/platform_lifecycle/environments/android/android_environment.py)).
   `device_pool`'s `lease()` closure wraps the value `launch_driver(...)` returns in a
   `TracingDriver`, right there, before storing it on `Lease.driver` — the same object `lease_env`'s
   teardown later receives.
   - That teardown call (`lease_env.end_lease` / `teardown`) could have forced a choice between
     wrapping only the value handed to `run_scenario()` and confirming `TracingDriver`'s
     transparency covers teardown too. It does not need to: every environment's `teardown` takes
     `driver` for interface shape alone and never reads it — each is marked
     `# noqa: ARG002  # Environment shape`
     ([`environments/ios.py:88`](../../bajutsu/common/platform_lifecycle/environments/ios.py),
     [`environments/android/android_environment.py:363`](../../bajutsu/common/platform_lifecycle/environments/android/android_environment.py)).
     Teardown reads only environment-owned state (`self._resident`, `self._serial`, the runner
     process), so `Lease.driver` can be wrapped once, uniformly, with no split between a raw value
     for teardown and a wrapped one for the step loop.
6. **Scenario and step boundaries** — two explicit calls, not monkey-patches, since this item edits
   both files directly:
   - `_ScenarioRunner.run_one` ([`pipeline.py`](../../bajutsu/common/runner/pipeline.py)) opens the
     thread-local trace context unit 2 introduced, keyed by the scenario's `sid`, only when
     `--trace-driver` is on (an off run never sets it, so `make_driver` and `AdbDriver`'s `run=`
     check unit 2 describes read "not tracing" at zero extra cost); in its `finally` it flushes the
     accumulated records through `self._artifacts()`
     ([`RunArtifactWriter.write_json`](../../bajutsu/common/evidence/sink.py)) to
     `f"{sid}/driver_trace.json"` — the run's single write boundary (BE-0331), which also means
     secret-scrubbing runs over the file for free even though no record currently carries
     scenario-authored text.
   - `_StepRunner._run_one`
     ([`bajutsu/common/orchestrator/loop/_step_runner.py`](../../bajutsu/common/orchestrator/loop/_step_runner.py))
     pushes/pops the current step's key onto the same thread-local context.
   - Thread-local state is sufficient because `_ScenarioRunner.run_one` runs entirely on one
     `ThreadPoolExecutor` worker thread per scenario (`pipeline.py`'s `run_all`): a thread is never
     mid-scenario for two scenarios at once, so "the active trace context on this thread" always
     means "this scenario, right now" — and it is the same thread `launch_driver`/`make_driver` run
     on for that scenario's lease, so unit 2's read of it during driver construction sees the right
     scenario's context.
7. **CLI flag** — `bajutsu run --trace-driver` (`bajutsu/run/cli.py`), threaded through `_RunPlan`
   to `_ScenarioRunner` (the field that gates unit 6's `open`/`flush` calls), following the same
   "diagnostic-only, off by default" pattern as `--score` and `--zip`.

### Output shape

`runs/<run_id>/<sid>/driver_trace.json`:

```json
{
  "scenario": "<scenario name>",
  "steps": [{"step": "00:tap", "wall_s": 1.02}],
  "records": [
    {"category": "driver", "step": "00:tap", "name": "tap", "started_at": 1234567890.1, "elapsed_s": 0.69},
    {"category": "transport", "step": "00:tap", "name": "POST /tap", "started_at": 1234567890.1, "elapsed_s": 0.62, "response": {"status": "ok"}}
  ]
}
```

No file is written for a scenario run without `--trace-driver` — the flag's off-path costs nothing
beyond the flag check itself.

## Alternatives considered

| Alternative | Why we did not take it |
|---|---|
| Promote `trace_run.py`'s own monkey-patching into a permanent module inside `bajutsu` | It reaches into private module internals (`_raw_http_transport`, `adb_resident.ResidentServer.start`) that are free to change shape since nothing outside `trace_run.py` today depends on them; making that a permanent contract trades a script's disposable fragility for a maintained one. |
| Add timing code directly inside every `XcuitestDriver` / `AdbDriver` method body | Touches roughly twenty methods across two files that already carry real actuation logic, for a diagnostic feature — a much larger, riskier diff than composing at the one seam (`make_driver`) both backends already construct through. |
| Thread an explicit `trace` parameter through `backends.make_driver`, `launch_driver`, `RunEnvironment`, and every concrete environment's constructor, instead of a thread-local | The more conventional dependency-injection shape, and the one this item's earlier draft assumed `device_pool`'s own `make_driver` argument already gave it (it does not — see unit 5). Actually wiring it this way touches the public constructor of every `RunEnvironment` subclass (`XcuitestEnvironment`, `AndroidEnvironment`, `WebEnvironment`, `FakeEnvironment`) for a diagnostic feature. The thread-local unit 2 uses instead is a smaller, more contained change, at the cost of the seam being implicit rather than an explicit argument. |
| Measure evidence-write timing (`FileSink.capture`) as a fourth category, matching `trace_run.py` | The driver calls evidence capture makes (`screenshot`, `query`) are already visible under `driver`; the remainder is file I/O and redaction overhead, which is not "operating the simulator or emulator" — outside this item's motivation. Left for a future item if evidence-write latency itself is ever the suspect. |
| Cover the web (Playwright) backend too, for architectural symmetry | This item's motivation is specifically simulator/emulator operation latency; Playwright's browser communication is internal to its own Python binding, not a round trip bajutsu's driver code initiates. The `Driver` protocol boundary a `TracingDriver` wraps would still work for `PlaywrightDriver` if a future item wants it. |
| Enable by an environment variable (`BAJUTSU_DRIVER_TRACE=1`), matching `BAJUTSU_LOG_LEVEL` / `BAJUTSU_STALL_DIAGNOSTICS` | Considered for consistency with those two existing opt-in diagnostics. A CLI flag was chosen instead so the choice is visible in a run's own command line and in CI configuration, rather than in an environment an operator has to know to check. |
| Record a `transport` POST record's full reply body, not just the small structured outcome | Would answer more questions from one trace file (e.g., exactly which fold `/tap` folded in). Rejected because the body an `/elements` or `/act` reply can carry is already captured as the run's own evidence (`elements.json`); duplicating it into `driver_trace.json` risks a diagnostic artifact larger than the run it diagnoses, for content this item's motivation (round-trip counts and durations) does not need. |

## Progress

> Keep this current as work proceeds. The checklist mirrors the MECE work breakdown in
> *Detailed design* (one box per unit of work); the log records what changed and when
> (oldest first), linking the PRs.

- [x] Unit 1 — `TracingDriver`, a `base.Driver`-conforming delegating proxy that declares no
      protocol methods of its own (`__getattr__` only), timing a call only when the wrapped driver
      actually has it, so `isinstance` against a capability protocol (`InterruptionPolicyTarget`,
      `SettledReadProvider`, …) still reads the wrapped driver's real capability set.
- [x] Unit 2 — The shared thread-local trace context `make_driver` and `AdbDriver`'s `run=` wrap
      consult, set by unit 6's `_ScenarioRunner.run_one` hook.
- [x] Unit 3 — `transport`-category timing on iOS: a new optional constructor argument on
      `XcuitestDriver`, wrapping `self._transport` a second time alongside the existing
      `_tracking_transport` wrap, recording `_Reply.status` for a POST; `backends.make_driver`'s
      `xcuitest` branch passes it when unit 2's context says tracing is on.
- [x] Unit 4 — `transport`- and `subprocess`-category timing on Android, both inside
      `backends.make_driver`'s `adb` branch: wrap `fetch_hierarchy` / `fetch_clock` / `act`
      (`transport`, the `act` wrap also recording `ActOutcome.acted` / `.published_mark`) and pass a
      timed `adb.real_run` as `AdbDriver`'s `run=` (`subprocess`); also
      substitute `AdbDriver._run_text`'s class-level attribute for the one call `run=` does not
      reach. No monkey-patch of `subprocess` in any module.
- [x] Unit 5 — The `driver`-category wrap: `device_pool`'s `lease()` closure wraps the value
      `launch_driver(...)` returns in a `TracingDriver`, before storing it on `Lease.driver`
      (teardown never reads that argument, confirmed in Detailed design unit 5).
- [x] Unit 6 — Scenario and step boundary hooks in `_ScenarioRunner.run_one` and
      `_StepRunner._run_one`: open/flush the trace context (unit 2) and `driver_trace.json` write
      through `RunArtifactWriter.write_json`.
- [x] Unit 7 — The `bajutsu run --trace-driver` CLI flag, threaded through `_RunPlan` to
      `_ScenarioRunner`.
- [x] Unit 8 — Tests: a `TracingDriver` unit test against `FakeDriver`, including that wrapping
      preserves a capability-protocol negative (`isinstance(traced, base.SettledReadProvider)`
      stays False); an `XcuitestDriver` built with a stub `transport`, asserting a `transport`
      record per round trip; an `AdbDriver` built with a fake `run`, asserting a `subprocess`
      record per adb invocation; a `--trace-driver` run against the `fake` backend asserting the
      written file's shape; a no-flag run asserting no `driver_trace.json` is written. The `fake`
      backend alone would leave units 3–4 (the iOS and Android wraps) with no fast-suite coverage,
      since it produces no `transport` or `subprocess` records.
- [x] Unit 9 — Documentation: the CLI reference for `bajutsu run`'s flags, in both languages, gains
      `--trace-driver`.

## References

- [BE-0407 — Cut step latency by deduplicating evidence reads and tuning driver internals (iOS and Android)](../BE-0407-step-latency-driver-internal-tuning/BE-0407-step-latency-driver-internal-tuning.md)
- [`trace_run.py`](../BE-0407-step-latency-driver-internal-tuning/misc/step-performance/trace_run.py) — the investigation script this item makes a permanent, per-scenario feature
