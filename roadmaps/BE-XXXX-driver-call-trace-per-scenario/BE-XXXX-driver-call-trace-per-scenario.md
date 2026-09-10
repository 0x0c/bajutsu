**English** · [日本語](BE-XXXX-driver-call-trace-per-scenario-ja.md)

# BE-XXXX — Trace Python↔driver calls per scenario, permanently

<!-- BE-METADATA -->
| Field | Value |
|---|---|
| Proposal | [BE-XXXX](BE-XXXX-driver-call-trace-per-scenario.md) |
| Author | [@0x0c](https://github.com/0x0c) |
| Status | **Proposal** |
| Tracking issue | [Search](https://github.com/bajutsu-e2e/bajutsu/issues?q=is%3Aissue+label%3Aroadmap-tracking+in%3Atitle+"BE-XXXX") |
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
Unlike `trace_run.py`, none of this is monkey-patched: every seam it uses is a dependency-injection
point the orchestrator already has, mostly built for testing (BE-0143) or for BE-0407's own
drain-tracking wrapper.

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
  …), plus the two non-protocol methods `trace_run.py` also measured (`drain_interruptions`,
  `settled_query`) that the orchestrator calls directly on a concrete driver.
- **`transport`** — one record per host-device round trip *inside* a single driver method call. A
  `query()` call that also fetches `/zorder` produces two `transport` records under one `driver`
  record; a `tap()` call that resolves cleanly produces one.
- **`subprocess`** — Android only. A `uiautomator dump` fallback
  ([`bajutsu/common/drivers/adb/hierarchy_read.py:8-10`](../../bajutsu/common/drivers/adb/hierarchy_read.py))
  or an `adb shell` command issued outside the resident-server channel
  ([`bajutsu/common/backend_cli/adb/_functions.py:111-112`](../../bajutsu/common/backend_cli/adb/_functions.py)).
  iOS's `simctl`/`xcodebuild` process spawns happen once at device lease, before any scenario's
  steps run, so they carry no per-step signal and are not measured.

Every record carries `{category, step, name, started_at, elapsed_s}`: `step` is the step index and
kind (`f"{i:02d}:{kind}"`, matching `trace_run.py`'s own key) the call happened during, `started_at`
is a wall-clock Unix timestamp (so a record can be cross-referenced against `device.log` or the
step's own `started_at` in `manifest.json`), and `elapsed_s` is the call's own duration.

### Composition over monkey-patching

`trace_run.py` has to monkey-patch, because it is an external script that cannot edit
`bajutsu`'s own source. This item can, and the orchestrator already exposes the seams a permanent
version of the same measurement needs — none of them new, all added for testability or by BE-0407
itself:

1. **`TracingDriver`** (new) — a `base.Driver`-conforming delegating proxy. Every protocol method,
   plus `drain_interruptions`/`settled_query`, times the call before delegating and records a
   `driver`-category entry against the currently active step (below); every other attribute access
   (`.name`, `.device_os`, …) falls through via `__getattr__`, so nothing besides timing changes for
   a caller holding one.
2. **`transport` on iOS** —
   [`XcuitestDriver.__init__`](../../bajutsu/common/drivers/xcuitest/xcuitest_driver.py) already
   wraps its own `self._transport` in a delegating closure, `_tracking_transport`, to fold
   BE-0407 Unit 6's drain-tracking in. This item adds one more optional constructor argument (e.g.
   `on_transport_call: Callable[[str, float, float], None] | None`), applied as a second wrap in the
   same place, active only when `--trace-driver` passed it — no change to `_raw_http_transport` or
   any other module.
3. **`transport` on Android** —
   [`backends.make_driver`](../../bajutsu/common/backends.py)'s `adb` branch already receives
   `fetch_hierarchy` / `fetch_clock` / `act` as plain callables from its caller and forwards them
   to `AdbDriver(...)` unchanged. When tracing is on, `make_driver` wraps each of the three with a
   timing decorator before the call to `AdbDriver(...)` — `AdbDriver`'s own source does not change.
4. **`subprocess` on Android** — the one category with no existing injection point, since
   `real_run` and the `uiautomator dump` fallback are called from several places inside
   `bajutsu.common.backend_cli.adb` and `bajutsu.common.drivers.adb`, not handed in as a parameter.
   Scoped to that one module's own `subprocess.run` / `subprocess.check_output` names, replaced only
   for the lifetime of a `--trace-driver` run and only within that module's namespace — the same
   trade-off `trace_run.py` already made, just contained to one module instead of the whole process.
5. **Injection point** — `bajutsu.common.runner.pool.device_pool` already takes an injectable
   `make_driver` argument (`Callable[..., base.Driver] = _make_driver`), added for tests. When
   `--trace-driver` is set, `bajutsu/run/cli.py`'s dispatch functions pass a wrapper that calls the
   real `make_driver` (with the transport wraps from units 2–3 threaded through) and returns a
   `TracingDriver` around the result.
   - `pool.py`'s `Lease.driver` also flows into this environment's own teardown
     (`lease_env.end_lease` / `teardown`), which could have forced a choice between wrapping only the
     value handed to `run_scenario()` and confirming `TracingDriver`'s transparency covers teardown
     too. It does not: every environment's `teardown` takes `driver` for interface shape alone and
     never reads it — each is marked `# noqa: ARG002  # Environment shape`
     ([`environments/ios.py:88`](../../bajutsu/common/platform_lifecycle/environments/ios.py),
     [`environments/android/android_environment.py:363`](../../bajutsu/common/platform_lifecycle/environments/android/android_environment.py)).
     Teardown reads only environment-owned state (`self._resident`, `self._serial`, the runner
     process), so `Lease.driver` can be wrapped once, uniformly, with no split between a raw value
     for teardown and a wrapped one for the step loop.
6. **Scenario and step boundaries** — two explicit calls, not monkey-patches, since this item edits
   both files directly:
   - `_ScenarioRunner.run_one` ([`pipeline.py`](../../bajutsu/common/runner/pipeline.py)) opens a
     thread-local trace context keyed by the scenario's `sid` at the top, and in its `finally`
     flushes the accumulated records through `self._artifacts()`
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
     means "this scenario, right now".
7. **CLI flag** — `bajutsu run --trace-driver` (`bajutsu/run/cli.py`), threaded through `_RunPlan`
   into `device_pool(...)`, following the same "diagnostic-only, off by default" pattern as
   `--score` and `--zip`.

### Output shape

`runs/<run_id>/<sid>/driver_trace.json`:

```json
{
  "scenario": "<scenario name>",
  "steps": [{"step": "00:tap", "wall_s": 1.02}],
  "records": [
    {"category": "driver", "step": "00:tap", "name": "tap", "started_at": 1234567890.1, "elapsed_s": 0.69},
    {"category": "transport", "step": "00:tap", "name": "POST /tap", "started_at": 1234567890.1, "elapsed_s": 0.62}
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
| Cover `transport` and `subprocess` the same way (an injectable parameter, no monkey-patching at all) | Feasible for `transport` (units 2–3 above), which is why this item takes that route there. Not feasible for `subprocess` without widening `real_run`'s and the `uiautomator dump` fallback's signatures across every call site inside `backend_cli/adb`, which is more invasive than a monkey-patch scoped to that module alone. |
| Measure evidence-write timing (`FileSink.capture`) as a fourth category, matching `trace_run.py` | The driver calls evidence capture makes (`screenshot`, `query`) are already visible under `driver`; the remainder is file I/O and redaction overhead, which is not "operating the simulator or emulator" — outside this item's motivation. Left for a future item if evidence-write latency itself is ever the suspect. |
| Cover the web (Playwright) backend too, for architectural symmetry | This item's motivation is specifically simulator/emulator operation latency; Playwright's browser communication is internal to its own Python binding, not a round trip bajutsu's driver code initiates. The `Driver` protocol boundary a `TracingDriver` wraps would still work for `PlaywrightDriver` if a future item wants it. |
| Enable by an environment variable (`BAJUTSU_DRIVER_TRACE=1`), matching `BAJUTSU_LOG_LEVEL` / `BAJUTSU_STALL_DIAGNOSTICS` | Considered for consistency with those two existing opt-in diagnostics. A CLI flag was chosen instead so the choice is visible in a run's own command line and in CI configuration, rather than in an environment an operator has to know to check. |

## Progress

> Keep this current as work proceeds. The checklist mirrors the MECE work breakdown in
> *Detailed design* (one box per unit of work); the log records what changed and when
> (oldest first), linking the PRs.

- [ ] Unit 1 — `TracingDriver`, a `base.Driver`-conforming delegating proxy timing the protocol
      methods plus `drain_interruptions`/`settled_query`, with `__getattr__` fallthrough for
      everything else.
- [ ] Unit 2 — `transport`-category timing on iOS: a new optional constructor argument on
      `XcuitestDriver`, wrapping `self._transport` a second time alongside the existing
      `_tracking_transport` wrap.
- [ ] Unit 3 — `transport`-category timing on Android: wrap `fetch_hierarchy` / `fetch_clock` / `act`
      inside `backends.make_driver`'s `adb` branch before constructing `AdbDriver`.
- [ ] Unit 4 — `subprocess`-category timing on Android: a `--trace-driver`-scoped monkey-patch of
      `subprocess.run` / `subprocess.check_output` local to `bajutsu.common.backend_cli.adb`.
- [ ] Unit 5 — Injection wiring: a `make_driver` wrapper passed to `device_pool(...)` under
      `--trace-driver`, wrapping `Lease.driver` uniformly (teardown never reads it).
- [ ] Unit 6 — Scenario and step boundary hooks in `_ScenarioRunner.run_one` and
      `_StepRunner._run_one`, writing `driver_trace.json` through `RunArtifactWriter.write_json`.
- [ ] Unit 7 — The `bajutsu run --trace-driver` CLI flag, threaded through `_RunPlan`.
- [ ] Unit 8 — Tests: a `TracingDriver` unit test against `FakeDriver`; a `--trace-driver` run
      against the `fake` backend asserting the written file's shape; a no-flag run asserting no
      `driver_trace.json` is written.
- [ ] Unit 9 — Documentation: the CLI reference for `bajutsu run`'s flags, in both languages, gains
      `--trace-driver`.

## References

- [BE-0407 — Cut step latency by deduplicating evidence reads and tuning driver internals (iOS and Android)](../BE-0407-step-latency-driver-internal-tuning/BE-0407-step-latency-driver-internal-tuning.md)
- [`trace_run.py`](../BE-0407-step-latency-driver-internal-tuning/misc/step-performance/trace_run.py) — the investigation script this item makes a permanent, per-scenario feature
