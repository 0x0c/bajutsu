**English** · [日本語](BE-XXXX-xcuitest-crash-report-scenario-artifact-ja.md)

# BE-XXXX — Copy the iOS runner's crash report into the failed scenario's run directory

<!-- BE-METADATA -->
| Field | Value |
|---|---|
| Proposal | [BE-XXXX](BE-XXXX-xcuitest-crash-report-scenario-artifact.md) |
| Author | [@0x0c](https://github.com/0x0c) |
| Status | **Proposal** |
| Tracking issue | [Search](https://github.com/bajutsu-e2e/bajutsu/issues?q=is%3Aissue+label%3Aroadmap-tracking+in%3Atitle+"BE-XXXX") |
| Topic | Platform support |
| Related | [BE-0361](../BE-0361-ios-ci-simulator-diagnostics/BE-0361-ios-ci-simulator-diagnostics.md), [BE-0319](../BE-0319-xcuitest-cold-spawn-resilience/BE-0319-xcuitest-cold-spawn-resilience.md), [BE-0415](../BE-0415-driver-call-trace-per-scenario/BE-0415-driver-call-trace-per-scenario.md) |
<!-- /BE-METADATA -->

## Introduction

The resident XCUITest runner sometimes dies mid-scenario, and the run pipeline's crash-recovery
retries sometimes exhaust without a recovery. When that happens, `bajutsu run` builds the
scenario's failure message from the crash error alone. It names the fact that the runner died, but
it carries no runner-log path, no log content, and no mention of the report macOS itself writes for
a process that faults. Two pieces of direct evidence do exist on disk at that moment: the runner's
own captured output, and — when the host process itself faulted — the crash report macOS wrote for
it. Neither reaches the scenario's own run directory (`runs/<run_id>/<sid>/`), where every other
piece of that scenario's evidence already lives. This item copies both into that directory. A
contributor debugging a red scenario then finds the runner's own failure evidence next to the
screenshots and element trees the same run already produced — no digging through warning-level
logs for a path, no re-running the scenario with extra diagnostics enabled just to see what the
runner process actually did.

## Motivation

[BE-0361](../BE-0361-ios-ci-simulator-diagnostics/BE-0361-ios-ci-simulator-diagnostics.md) already
built a layered diagnostics collection for the iOS lanes of continuous integration (CI). Its first
layer — a result bundle per runner spawn, a bounded stall-time probe — is opt-in, behind an
environment variable a CI workflow sets. Its other two layers are not: a composite GitHub Actions
step already runs on every iOS job, unconditionally, sweeping the macOS host's own crash-report and
log stores (`.github/actions/collect-ios-diagnostics/action.yml`). So CI already gathers a runner
crash report today, in the common case.

That collection still leaves two gaps this item closes. First, it is job-wide, not scenario-wide:
it tars up everything `~/Library/Logs/DiagnosticReports` held for the whole job, so a job that ran a
dozen scenarios gives a contributor no way to tell which crash report belongs to which failing
scenario, if more than one crashed. Second, it is CI-only shell code with no counterpart in
`bajutsu` itself, so a developer reproducing a crash with a local `bajutsu run` gets nothing at
all — not even the pointer BE-0319's own runner-log capture already writes to a log file, since
that pointer never reaches the scenario's own failure message or report; it reaches only a
warning-level log line
([`_runner_log_hint`](../../bajutsu/common/platform_lifecycle/environments/xcuitest/xcuitest_environment.py)),
which a failed run may never have surfaced.

The crash report itself exists because XCUITest's host process (`xcodebuild test-without-building`)
is an ordinary macOS process. When it terminates on a fault rather than an orderly exit — as
opposed to exiting with a test-failure code, the far more common shape a stalled screenshot service
produces — the operating system writes a `.ips` crash report under
`~/Library/Logs/DiagnosticReports`, naming the terminating signal and, for system frames, a
symbolicated stack trace. It is the one piece of direct evidence a genuine process fault produces,
narrower and rarer than the ordinary "the channel stopped answering" crash this item's own scope
otherwise covers.

This item's observable outcome: a scenario that fails on an exhausted crash retry gains a
`crash-diagnostics/` subdirectory under its own `runs/<run_id>/<sid>/`, holding the runner's full
captured output and, whenever macOS wrote one for the `xcodebuild` process, its `.ips` crash
report. The scenario's own failure string also names that subdirectory, so a contributor reading
the failure never has to already know it exists. Today neither the subdirectory nor that mention
exists at all.

## Detailed design

### A method every environment defines, following the shape the crash-recovery layer already uses

`RunEnvironment`
([`bajutsu/common/platform_lifecycle/protocols/run_environment.py`](../../bajutsu/common/platform_lifecycle/protocols/run_environment.py))
is a structural `Protocol`. No concrete environment subclasses it, so a method's body there binds
to nobody — every "no-op by default" method on it, `request_device_replacement` and
`replaced_device` (BE-0354) included, is written out separately in each concrete class:
`_DeviceEnvironment` ([`ios.py`](../../bajutsu/common/platform_lifecycle/environments/ios.py),
shared by the Simulator XCUITest backend and the fake test backend), `WebEnvironment`
([`web.py`](../../bajutsu/common/platform_lifecycle/environments/web.py)), and
`AndroidEnvironment`
([`android_environment.py`](../../bajutsu/common/platform_lifecycle/environments/android/android_environment.py)).
This item adds `crash_artifacts()` to the protocol's declared shape and to all three of those
classes, each returning `[]`:

```python
def crash_artifacts(self) -> list[tuple[str, bytes]]:
    """Files this environment captured for its last backend crash, or [] when it has none."""
    return []
```

`XcuitestEnvironment` overrides it, the same way it already overrides `_DeviceEnvironment`'s
`request_device_replacement` (`xcuitest_environment.py:500`).

### Snapshotting at crash detection, not reading live state later

The pipeline's crash-recovery retry loop, `_run_one_impl`
([`bajutsu/common/runner/pipeline.py`](../../bajutsu/common/runner/pipeline.py)), releases the
crashed lease back to the pool — `free.put(udid)` — inside `_run_on_lease`'s own `finally`,
*before* the loop decides whether to retry. A `crash_artifacts()` that read `self._runner_log` /
`self._runner_proc` lazily, only when the loop finally gives up, would race a concurrent worker on
a multi-device run: that worker's own next lease can reuse this exact environment instance (`pool.py`
keys its warm cache by udid) and respawn a fresh runner on it before this scenario's retry loop ever
reads back the old crash's evidence — clearing `self._runner_log` and `self._runner_proc`
(`_discard_runner`, `xcuitest_environment.py:1142`) and, for a healthy respawn, leaving nothing
crash-related behind at all.

So `XcuitestEnvironment` captures eagerly instead, at the point `_discard_runner` itself first
observes the crash — where it already sets `crashed = True` and logs "a mid-run crash"
(`xcuitest_environment.py:1170-1176`), before `self._runner_proc = None` clears the handle a few
lines later. Right there, it reads the two entries below and caches them as
`self._last_crash_artifacts`; `crash_artifacts()` just returns that cached list. Both entries are
best-effort, matching the posture `_result_bundle_path` and `_capture_stall` already take for their
own captures — a missing log, an unreadable `DiagnosticReports` directory (any platform but macOS,
or a sandboxed CI runner with no read permission), or no crash report at all (the process never
actually faulted — the channel just stopped answering) each resolve to that entry being skipped,
never to a raise:

- **The runner's own captured output**, read in full from `self._runner_log`, the file
  `_open_runner_output` opens. Captured by default today (BE-0319), but never copied anywhere.
- **The `xcodebuild test-without-building` process's own macOS crash report.** `_spawn_runner`
  already records the process handle as `self._runner_proc` right after `Popen` returns
  (`xcuitest_environment.py:766`); this item adds a spawn タイムスタンプ next to it,
  `self._runner_spawned_at = time.time()`, since `Popen` exposes no start time of its own. The
  capture lists `~/Library/Logs/DiagnosticReports` for a `.ips` file named `xcodebuild-*`, whose
  modification time falls at or after `self._runner_spawned_at`; the name-and-time match keeps the
  sweep from picking up an unrelated `xcodebuild` invocation's report left on the same host. When
  the file's own JavaScript Object Notation (JSON) header names a `pid`, matching it against
  `self._runner_proc.pid` narrows a
  multi-worker host's several concurrent `xcodebuild` processes further, but a report whose header
  cannot be parsed is still taken on the name-and-time match alone — this capture stays best-effort
  throughout. The listing is capped at the first few matches, mirroring BE-0361's own per-capture
  caps, so a runner that keeps crash-looping cannot make one scenario's evidence write unbounded.

This ordering is what a released, then re-leased, environment cannot undo: the snapshot is already
taken and cached before `free.put(udid)` runs, so a later respawn's own state changes never touch
it. One narrow gap remains, inherent to caching on the environment instance rather than per
scenario: if the *same* environment crashes again, on a different scenario, before the first
scenario's retry loop reads `crash_artifacts()` back, the second crash's snapshot overwrites the
first's. That needs two crash-recovery episodes racing on one shared warm environment across
workers, which BE-0354's own device-replacement rung already treats as a degraded-device escalation
case rather than an ordinary retry — left as an accepted, narrow limitation of a best-effort
capture, not a target for this item to close.

### Reaching the scenario's own writer

`_run_one_impl` already holds both pieces this item needs to write the cached snapshot out: `sid`,
the scenario's own evidence-directory name, and `lz`, the `Lease` the crashed attempt ran on.
`Lease` ([`bajutsu/common/runner/types.py`](../../bajutsu/common/runner/types.py)) gains one more
field, given a module-level no-op default the way `relaunch`/`control` neighbors already are:

```python
def _no_crash_artifacts() -> list[tuple[str, bytes]]:
    return []

# on Lease:
crash_artifacts: Callable[[], list[tuple[str, bytes]]] = _no_crash_artifacts
```

`pool.py`'s `lease()` closure wires it the same way it already wires
`request_device_replacement=lease_env.request_device_replacement` (`pool.py:556`) — a bound method
reference, not a call, so nothing runs until the pipeline actually asks for it.

The pipeline asks for it once: where the retry loop gives up and builds the scenario's terminal
`RunResult(ok=False, ...)` for a backend crash it could not recover — the `if device_timeout ...
elif ... else:` chain that already sets `failure` for that case. Right there, when `lz is not None`
and `self._artifacts()` returns a writer, the pipeline calls `lz.crash_artifacts()` before
returning that `RunResult`. For each `(name, content)` pair it writes through
`writer.write_text(f"{sid}/crash-diagnostics/{name}", content.decode(errors="replace"))` — the same
per-scenario write shape
[BE-0415](../BE-0415-driver-call-trace-per-scenario/BE-0415-driver-call-trace-per-scenario.md)
already uses for `driver_trace.json` — and it uses `write_text` rather than `write_bytes` so the
free-text scrub (BE-0331) still runs over content this item did not author. It also appends the
subdirectory's path to `failure` itself, so the failure string a contributor actually reads points
at the new evidence directly, closing the gap Motivation named. A logger — never a raise — catches
a write problem, such as a full disk or a permissions error, because a diagnostic artifact must
never turn an already-decided failure into a different, unrelated one.

### Why once, not per attempt

BE-0361's stall probe fires at every crash: it investigates whether the *retry itself* is worth
trying. This item fires once, only when the retry loop has already given up. Its own evidence — the
runner's crash — names the same fact on every attempt of one crash-looping scenario. Copying it
after each attempt would leave a recovered scenario carrying crash evidence for a failure its own
final result no longer reports. A scenario that recovers within its retry budget passes, and a
passing scenario needs no crash report.

### Cost on every other backend

Android's and the web backend's environments return `[]` from their own `crash_artifacts()`, so the
pipeline's write step becomes a no-op list iteration, unchanged from today. The iOS backend itself
only ever constructs on macOS, so the `DiagnosticReports` sweep never runs on a Linux host at all.
Nothing in this item changes what a non-macOS run captures.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Gate the capture behind an environment variable, matching BE-0361's `BAJUTSU_XCUITEST_RESULT_BUNDLES` / `BAJUTSU_STALL_DIAGNOSTICS` | This item's own gap is the opposite of BE-0361 layer 1's: CI already gathers a crash report unconditionally (layers 2–3), and what is missing is a local-run counterpart and per-scenario attribution — neither served by an opt-in CI variable. The capture also runs only once a scenario is already ending in failure, so its cost is one bounded directory listing and one file copy — not a standing overhead worth gating. |
| Also copy the `.xcresult` result bundle BE-0361 unit 1 can produce | That bundle is already BE-0361's own opt-in artifact, behind `BAJUTSU_XCUITEST_RESULT_BUNDLES`, and is not bounded the way a `.ips` report is. Making it default-on here would add an unbounded artifact for content the `.ips` report and the runner's own log already summarize. Left for a future item if this one's evidence proves insufficient. |
| Capture at every crash-recovery attempt, not only the one that exhausts the budget | Rejected in *Why once, not per attempt* above. It duplicates for a scenario that eventually recovers. The scenario's crash-exhausted `RunResult` — the one place this evidence explains — exists only once, at the end of the loop. |
| A full `xcrun simctl diagnose`, `log collect`, or `sysdiagnose` sweep on crash | Rejected for the reason BE-0361's own *Alternatives considered* already gave and measured: `simctl diagnose` alone runs to 22–78 MB and about 15 seconds per booted device, and a `.logarchive` of a job's whole window runs to hundreds of megabytes. The process's own `.ips` report already names the terminating signal and, for system frames, a symbolicated stack trace, at a cost of a few kilobytes. |

## Progress

> Keep this current as work proceeds. The checklist mirrors the MECE work breakdown in
> *Detailed design* (one box per unit of work); the log records what changed and when
> (oldest first), linking the PRs.

- [ ] Unit 1 — `crash_artifacts()` on the `RunEnvironment` protocol shape and, returning `[]`, on
      `_DeviceEnvironment` (ios.py), `WebEnvironment`, and `AndroidEnvironment`.
- [ ] Unit 2 — `XcuitestEnvironment`'s override: a spawn タイムスタンプ (`self._runner_spawned_at`)
      recorded alongside `self._runner_proc`; the eager snapshot inside `_discard_runner`, cached as
      `self._last_crash_artifacts` before the crashed process handle is cleared; the runner-log read
      and the name-and-time `DiagnosticReports` sweep for `xcodebuild-*.ips`, both best-effort and
      bounded.
- [ ] Unit 3 — `Lease.crash_artifacts`, defaulted through a module-level `_no_crash_artifacts`, wired
      in `pool.py`'s `lease()` closure alongside `request_device_replacement`.
- [ ] Unit 4 — The `pipeline.py` call site: invoked once, at the crash-exhausted `RunResult`, writing
      each artifact through `RunArtifactWriter.write_text` under `f"{sid}/crash-diagnostics/"` and
      appending that path to the `failure` string, with a write failure logged rather than raised.
- [ ] Unit 5 — Docs: the CI diagnostics section BE-0361 added to `docs/ci.md` (and its `docs/ja/`
      mirror) gains a note on this default-on, per-scenario counterpart.
- [ ] Unit 6 — Tests: `XcuitestEnvironment`'s crash snapshot against a stubbed `DiagnosticReports`
      directory (the name-and-time match, the pid refinement, the cap, the missing-log and
      missing-report cases); a test that a second crash on a shared environment overwrites the first
      scenario's cached snapshot, pinning the documented limitation; a `pipeline.py` test asserting a
      crash-exhausted scenario's run directory gains `crash-diagnostics/` and its path in `failure`;
      a recovered-scenario test asserting it does not; an Android/web/fake-backend test asserting the
      call site's no-op default is unchanged.

## References

- [BE-0361](../BE-0361-ios-ci-simulator-diagnostics/BE-0361-ios-ci-simulator-diagnostics.md) — the
  CI-scoped diagnostics layers this item complements with a default-on, per-scenario one; also the
  source of the `simctl diagnose` and `log collect` costs *Alternatives considered* cites
- [BE-0319](../BE-0319-xcuitest-cold-spawn-resilience/BE-0319-xcuitest-cold-spawn-resilience.md) —
  the default-on runner-output capture this item copies into the scenario directory
- [BE-0354](../BE-0354-xcuitest-wedge-fastfail-device-replacement/BE-0354-xcuitest-wedge-fastfail-device-replacement.md) —
  `request_device_replacement`, the existing method whose per-class no-op shape this item's
  `crash_artifacts()` follows, and whose device-replacement escalation bounds the narrow
  shared-environment limitation *Detailed design* accepts
- [BE-0415](../BE-0415-driver-call-trace-per-scenario/BE-0415-driver-call-trace-per-scenario.md) —
  the per-scenario `RunArtifactWriter` write shape this item follows
- [`bajutsu/common/platform_lifecycle/environments/xcuitest/xcuitest_environment.py`](../../bajutsu/common/platform_lifecycle/environments/xcuitest/xcuitest_environment.py) —
  `_runner_log`, `_runner_proc`, `_discard_runner`, `_runner_log_hint`, the seams this item reads
- [`bajutsu/common/platform_lifecycle/environments/ios.py`](../../bajutsu/common/platform_lifecycle/environments/ios.py) —
  `_DeviceEnvironment`, whose own `request_device_replacement` no-op this item's default mirrors
- [`bajutsu/common/runner/pipeline.py`](../../bajutsu/common/runner/pipeline.py) — `_run_one_impl`,
  whose crash-exhausted `RunResult` is this item's one call site, and whose `_run_on_lease` releases
  the crashed lease before the retry loop decides whether to retry
- [`bajutsu/common/runner/pool.py`](../../bajutsu/common/runner/pool.py) — the `lease()` closure
  that wires `Lease.crash_artifacts` the same way it wires `request_device_replacement`
- [`bajutsu/common/platform_lifecycle/protocols/run_environment.py`](../../bajutsu/common/platform_lifecycle/protocols/run_environment.py) —
  the protocol `crash_artifacts()` joins, next to `request_device_replacement` and
  `replaced_device`
- [`bajutsu/common/evidence/sink.py`](../../bajutsu/common/evidence/sink.py) — `RunArtifactWriter`,
  the single write boundary (BE-0331) this item's artifacts cross
- [`.github/actions/collect-ios-diagnostics/action.yml`](../../.github/actions/collect-ios-diagnostics/action.yml) —
  BE-0361's already-unconditional `DiagnosticReports` sweep, whose job-wide scope Motivation
  contrasts with this item's per-scenario one
