**English** · [日本語](BE-XXXX-run-watch-mode-ja.md)

# BE-XXXX — `run --watch`: hold the device open across authoring iterations

<!-- BE-METADATA -->
| Field | Value |
|---|---|
| Proposal | [BE-XXXX](BE-XXXX-run-watch-mode.md) |
| Author | [@0x0c](https://github.com/0x0c) |
| Status | **Proposal** |
| Tracking issue | [Search](https://github.com/bajutsu-e2e/bajutsu/issues?q=is%3Aissue+label%3Aroadmap-tracking+in%3Atitle+"BE-XXXX") |
| Topic | Authoring experience |
| Related | [BE-0291](../BE-0291-xcuitest-runner-reuse-across-scenarios/BE-0291-xcuitest-runner-reuse-across-scenarios.md), [BE-0262](../BE-0262-serve-author-live-step-picker/BE-0262-serve-author-live-step-picker.md), [BE-0321](../BE-0321-test-impact-analysis/BE-0321-test-impact-analysis.md), [BE-0354](../BE-0354-xcuitest-wedge-fastfail-device-replacement/BE-0354-xcuitest-wedge-fastfail-device-replacement.md), [BE-0174](../BE-0174-scenario-ref-path-containment/BE-0174-scenario-ref-path-containment.md), [BE-0069](../BE-0069-executable-contributor-guardrails/BE-0069-executable-contributor-guardrails.md) |
<!-- /BE-METADATA -->

## Introduction

Authoring a scenario is a loop: edit the YAML, run it, read the failure, edit again. Every turn of
that loop is a fresh `bajutsu run` process, and every fresh process boots a device pool, cold-starts
a runner, and tears both down again. This item adds `run --watch`, which re-runs the same scenarios
when their files change while keeping the pool alive between iterations. It changes **when** a run
starts, never **what** a run does.

## Motivation

[BE-0291](../BE-0291-xcuitest-runner-reuse-across-scenarios/BE-0291-xcuitest-runner-reuse-across-scenarios.md)
established that the runner's cold start is the largest fixed cost of an iOS run — a cold start on a
loaded continuous-integration host routinely exceeds ten seconds, and the driver allows up to 120 for
it — and removed it *within* a run by caching each device's environment in the pool
(`bajutsu/common/runner/pool.py:263`). The amortization is real and it is bounded by the pool's
lifetime: `device_pool` returns a `(lease, shutdown)` pair (`:142`), and `shutdown` fires when the
run ends.

An authoring loop is many runs, not one. So the loop pays in full, every iteration, the cost
BE-0291 removed from within a run — and it pays it for the smallest possible edit, including one
that changes a single selector. The amortization stops exactly where the human's iteration begins.

The second cost is smaller and more irritating. A scenario saved mid-edit is invalid YAML; the run
exits with a load error, and the author re-issues the command. Nothing about that round trip is
information the tool did not already have.

Once this ships, a reader can check it on the showcase suite: start `run --watch`, edit a scenario,
and the second iteration begins without a runner cold start, because the same device and the same
runner served the first. The verdict line each iteration prints is the one `bajutsu run` prints, and
each iteration writes its own run directory, so `trace` and `report` work on any of them.

## Detailed design

### An iteration is a whole run, cold

This is the design's one non-negotiable. Watch mode carries **infrastructure** across iterations —
the booted device, the resident runner, the browser context — and carries **no application state**
whatsoever. Every iteration leases as `run` leases today, which relaunches the app, and runs the
scenario from its first step through its `before` / `after` hooks
([BE-0392](../BE-0392-scenario-before-after-hooks/BE-0392-scenario-before-after-hooks.md)). There is
no resume, no "re-run from the failing step", and no reuse of the screen the previous iteration left
behind.

The reason is the second prime directive. A scenario that passes only because the previous iteration
left the app on the right screen is a scenario that passes for a reason no run in CI will reproduce,
and the author would be debugging against a state the deterministic gate never sees. The tempting
feature — resume from where it broke — is the one this item refuses, and it refuses it in the body
rather than leaving it to be discovered later.

### The pool moves up one scope

`device_pool`'s `(lease, shutdown)` pair is already the right seam: the watch loop builds the pool
once, calls `run_all` per iteration, and calls `shutdown` when the watch ends. Nothing inside a lease
changes, so per-lease teardown, network collection, evidence, and device control behave exactly as
they do in a single run. The work is to lift the pool's construction out of `run`'s body into
something both the single-shot and the watching path call — a refactor with no behavioral change,
worth landing as its own unit so the watch loop lands on top of a proven seam.

### What is watched, and how

The watched set is the scenario files named on the command line plus every file they reference —
their `use:` components and `dataFile` CSVs. That set is already computed exactly:
`load_expanded_scenarios` resolves each ref through `contained_ref`
(`bajutsu/common/scenario/load_expanded.py:21`), so the watcher records the paths that resolution
touched rather than guessing at a glob. When a file is added to the suite directory under a
directory-shaped invocation, it joins the set on the next iteration's load.

Change detection polls that set from the standard library. Nothing in the tree watches files today,
and a native watcher would be a new dependency on the deterministic path for a feature that has to
poll anyway.

The comparison is a content hash, not a timestamp. `serve` already keys a config cache on
`(st_mtime_ns, st_size)` and records what that misses (`bajutsu/serve/helpers.py:132`): "an edit that
preserves both (a same-size rewrite that also keeps the timestamp) won't be noticed, which is
acceptable for an operator-edited config." It is not acceptable here. The commonest edit in an
authoring loop is one character of a selector — `id: a.b` to `id: a.c` — which is same-size, so on a
coarse-timestamp filesystem the loop would reprint the previous iteration's verdict while the author
believed the new file ran. A hash over a few dozen small YAML files at a human's editing cadence
costs nothing worth saving. The stat pair is still read first, as a cheap filter before hashing.

The poll interval is a flag with a small default, debounced so a multi-file save is one iteration
rather than several.

### An invalid file does not end the session

A load error — invalid YAML, an unknown component, a ref outside the suite root — is reported with
the same message `run` would print, and the watch keeps waiting. This is most of the loop's value:
the state worth preserving is precisely the state a syntax error currently destroys. A device or
runner failure is different, and is handled the way the run path already handles it
([BE-0354](../BE-0354-xcuitest-wedge-fastfail-device-replacement/BE-0354-xcuitest-wedge-fastfail-device-replacement.md)):
a wedged session is detected and the device replaced, inside the pool, without ending the watch.
A longer-lived pool meets those paths more often than a single run does, which is a reason to reuse
them rather than to add a watch-specific recovery.

### The exit status is not a verdict

`run --watch` runs until interrupted; its exit status reports whether the watch shut down cleanly and
never encodes pass or fail. The per-iteration verdict line and each iteration's manifest are the
verdict, exactly as today. CI invokes `bajutsu run`, never `--watch`, and the flag is refused
alongside the flags that only make sense for a single archived run (`--zip`, `--upload-exec`), so
the shape cannot be mistaken for a gate. Prime directive 1 is untouched — no model is anywhere near
this, and nothing about how a verdict is reached changes.

### Its relationship to the Author editor

[BE-0262](../BE-0262-serve-author-live-step-picker/BE-0262-serve-author-live-step-picker.md) already
gives the `serve` Author editor target-scoped runs from the browser, and it has the same underlying
need: a device held open across a person's iterations. The two should share the lifted pool seam
rather than each growing one. This item builds the seam and the terminal loop; a follow-on can move
the editor onto it.

### Deliberately not in the first version

Re-running only the scenarios a change affects. `impact`
([BE-0321](../BE-0321-test-impact-analysis/BE-0321-test-impact-analysis.md)) is exactly the analysis
that would narrow the set, and joining the two is attractive — but a watch that silently skips a
scenario an author expected to run is worse than one that runs them all, and the first version has
no evidence about which narrowing an author would trust. The first version re-runs what the command
line named.

### Work breakdown (MECE)

1. **Lift the pool seam** — pool construction and `shutdown` moved out of `run`'s body, callable by
   both paths, with no behavioral change.
2. **The watched set** — recorded from the paths ref resolution touched, including a directory-shaped
   invocation's newly added files.
3. **The poll and debounce** — the stat filter, the content hash behind it, the interval flag, and
   the multi-file save collapsing to one iteration.
4. **The iteration loop** — verdict line, run directory, and run id per iteration; a load error
   reported without ending the session.
5. **Flag guards and exit status** — refusal alongside the single-run archival flags, and an exit
   status that reports shutdown rather than a verdict.
6. **Documentation** — the CLI reference entry, an authoring-loop note in the scenarios guide, and
   both Japanese mirrors.

## Alternatives considered

- **Re-run only from the failing step, reusing the app state on screen.** Rejected: it makes a
  scenario's outcome depend on the previous iteration, which is the determinism the second prime
  directive exists to protect. It would also produce a manifest that no CI run could reproduce, so
  the evidence an author debugged against would not be the evidence the gate produces.
- **Let an external file watcher re-invoke `bajutsu run`.** Genuinely available today, with no code
  at all, and worth naming for that reason. Rejected: it re-invokes the process, so it saves the
  author's keystrokes and none of the cold start, which is the cost this item exists to remove. It
  also cannot keep the session alive across a syntax error, because the process it restarts is the
  one that failed.
- **Add a native file-watching dependency.** Rejected: it puts a compiled dependency on the base
  install for a loop the standard library already covers at a human's editing cadence, over a suite
  of a few dozen files.
- **Build it into `serve` only.** Rejected: it would tie an authoring convenience to running a web
  server, and the terminal loop is where a scenario is most often edited. Sharing the seam gives the
  editor the same benefit without making the terminal path depend on the browser.

## Progress

> Keep this current as work proceeds. The checklist mirrors the MECE work breakdown in
> *Detailed design* (one box per unit of work); the log records what changed and when
> (oldest first), linking the PRs.

- [ ] The lifted pool seam, with no behavioral change.
- [ ] The watched set, recorded from ref resolution.
- [ ] The poll — stat filter, content hash, interval flag, and debouncing.
- [ ] The iteration loop, including load errors that do not end the session.
- [ ] Flag guards and the exit status.
- [ ] Documentation in both languages.

Open questions to settle while building:

- Whether an iteration should be interruptible — a save arriving mid-run either queues one more
  iteration or cancels the current one. Queueing is simpler and never abandons a partial run's
  evidence; cancelling is what an author reaching for a fix actually wants.
- Whether the watch should garbage-collect its own run directories, which accumulate one per
  iteration and are the most disposable evidence the tool produces.
- Whether `--watch` should also watch the config file. A config change alters the target the pool was
  built for, so the honest response is to rebuild the pool, which costs the cold start the item is
  about — worth doing, worth saying out loud when it happens.
- Whether the web backend needs anything beyond the pool lift, given that its lane is a browser
  context rather than a device.

## References

- [BE-0291 — Reuse the XCUITest runner across scenarios to amortize cold startup](../BE-0291-xcuitest-runner-reuse-across-scenarios/BE-0291-xcuitest-runner-reuse-across-scenarios.md)
  — the amortization this item extends from a run's lifetime to a session's.
- [BE-0262 — Live step-picking and target-scoped runs in the Author editor](../BE-0262-serve-author-live-step-picker/BE-0262-serve-author-live-step-picker.md)
  — the browser-side loop that should share the same pool seam.
- [BE-0321 — Test impact analysis (affected-step selection from a change)](../BE-0321-test-impact-analysis/BE-0321-test-impact-analysis.md)
  — the narrowing deliberately left out of the first version.
- [BE-0354 — Detect a wedged XCUITest session fast and escalate a repeated crash retry to a replacement device](../BE-0354-xcuitest-wedge-fastfail-device-replacement/BE-0354-xcuitest-wedge-fastfail-device-replacement.md)
  — the recovery a longer-lived pool leans on rather than duplicating.
- [BE-0392 — Independent before/after lifecycle hooks for scenarios](../BE-0392-scenario-before-after-hooks/BE-0392-scenario-before-after-hooks.md)
  — the per-scenario setup every iteration re-runs in full.
- [BE-0174 — Contain scenario component and data refs within the suite root](../BE-0174-scenario-ref-path-containment/BE-0174-scenario-ref-path-containment.md)
  — the ref resolution that already computes the watched set exactly.
- `bajutsu/common/runner/pool.py:92` (`device_pool`), `:142` (the `(lease, shutdown)` pair), `:263`
  (BE-0291's cached environment), `bajutsu/common/scenario/load_expanded.py:21` (`contained_ref`),
  `bajutsu/serve/helpers.py:132` (the stat-pair cache key and the hole it accepts),
  `bajutsu/run/cli.py:1336` (`--zip`).
