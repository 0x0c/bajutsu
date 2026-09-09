**English** · [日本語](BE-XXXX-job-scoped-binary-override-ja.md)

# BE-XXXX — Job-scoped binary artifact override, independent of the active config binding

<!-- BE-METADATA -->
| Field | Value |
|---|---|
| Proposal | [BE-XXXX](BE-XXXX-job-scoped-binary-override.md) |
| Author | [@paihu](https://github.com/paihu) |
| Status | **Proposal** |
| Tracking issue | [Search](https://github.com/bajutsu-e2e/bajutsu/issues?q=is%3Aissue+label%3Aroadmap-tracking+in%3Atitle+"BE-XXXX") |
| Topic | Configuration sourcing |
| Related | [BE-0393](../BE-0393-per-org-config-memory/BE-0393-per-org-config-memory.md), [BE-0413](../BE-0413-worker-app-binary-delivery/BE-0413-worker-app-binary-delivery.md), [BE-0268](../BE-0268-composable-upload-artifacts/BE-0268-composable-upload-artifacts.md), [BE-0160](../BE-0160-worker-credential-free-uploads/BE-0160-worker-credential-free-uploads.md) |
<!-- /BE-METADATA -->

## Introduction

A hosted `bajutsu serve` runs each job against the [target](../../docs/glossary.md#target-app-device)'s
`appPath` — the prebuilt app binary the config names. Today, a job gets a binary the org's serve does
not already hold in exactly one way: rebinding the org's **active config**. A rebind is not a per-job
choice: for a caller with no session — a shared-token or CI request — it replaces the **deployment's
fallback** binding, the one record every sessionless caller reads next; it also writes the org's
**remembered configuration**
([BE-0393](../BE-0393-per-org-config-memory/BE-0393-per-org-config-memory.md)), which a colleague's
next session inherits on first use.
[BE-0413](../BE-0413-worker-app-binary-delivery/BE-0413-worker-app-binary-delivery.md) then ships that
bound tree's binary to whichever worker leases the job.

This item adds a **per-job binary artifact override**: a request to `run` (or `record` / `crawl`) names
an already-stored `binary`-kind artifact by its sha256, and that job alone installs it at `appPath` —
leaving the org's active config, and every other job or session running against it, untouched.

## Motivation

Continuous integration (CI) commonly wants "the same scenarios and config, this build's binary" for
every run it triggers. Today's paths there —
[`POST /api/compose`](../BE-0268-composable-upload-artifacts/BE-0268-composable-upload-artifacts.md)
and the legacy single-zip `POST /api/upload` — both rebind the org's active config before every
dispatch. That rebind surfaces two distinct problems, not one.

First, every CI request is sessionless — it carries no login cookie — so every CI bind replaces the
same **deployment fallback** binding
([BE-0393](../BE-0393-per-org-config-memory/BE-0393-per-org-config-memory.md)). Two concurrent CI
dispatches against one deployment therefore contend for that one record: whichever bind lands last is
what the other caller's already-queued, not-yet-dispatched job resolves against, even though neither
caller meant to touch the other's job.

Second, a CI bind is not confined to the CI caller at all. The same rebind also writes the org's
**remembered configuration** (BE-0393 unit 6), which a colleague's *next* session inherits on first
use — so a build meant for one CI run can become the binary a human web-UI session opens against, with
no bind of that member's own in between.

A third gap sits underneath both.
[BE-0413](../BE-0413-worker-app-binary-delivery/BE-0413-worker-app-binary-delivery.md) ships a binary to
a remote worker in one case alone: when the leased job's binding is an
[`Upload`](../BE-0268-composable-upload-artifacts/BE-0268-composable-upload-artifacts.md), the
`binding.upload is not None` check `_register_and_dispatch` — the single tail every `start_*` funnels
through — makes before it stamps `Job.bundle`. A job dispatched off
a Git-sourced config carries no `bundle` at all, and neither does one off a local config whose scenario
travels as server-stored `materials`. Its remote worker writes the config and scenario text into a fresh
workspace (`_materialize` in `bajutsu/serve/server/worker_job.py`), then has no way to place a binary
there. The app must already sit on that worker's disk, or the config's `build:` command must fetch it —
a shell command, ungoverned outside the sandboxing an uploaded bundle's server commands already get
([BE-0090](../BE-0090-uploaded-config-command-execution/BE-0090-uploaded-config-command-execution.md)).
A binary the control plane already holds as a content-addressed artifact has no deterministic,
credential-free path onto that worker today.

All three gaps trace to one design choice. Binary delivery is entangled with *which config is bound*, when
the unit a caller actually wants to vary is the job. Untangling them lets a CI run and a human web UI
session share one org without stepping on each other. It also lets a materials-based job receive a
binary the same way an uploaded bundle's job already does.

**Verifiable outcome.** Dispatch two sessionless `run` jobs through the API at the same time against one
deployment, each naming a different `binary` artifact sha256 the caller uploaded moments earlier. Both
jobs finish, each having installed its own binary, and each run's manifest records its own overridden
sha256. The deployment's fallback binding is unchanged — a sessionless `GET /api/config` reports the
same value before and after both jobs return.

This fails today: with no per-job path, each caller would first have to rebind that one shared
fallback, so the second bind changes what the first caller's job resolves against instead of leaving it
alone.

## Detailed design

The work is mutually exclusive and collectively exhaustive (MECE) across three units: naming a
standalone artifact per job, delivering it to wherever the job runs, and the tests that pin the seam
down.

### Unit 1 — A per-job artifact reference that never touches the active binding

[BE-0268](../BE-0268-composable-upload-artifacts/BE-0268-composable-upload-artifacts.md) already lets a
`binary` artifact be uploaded and stored on its own. It is content-addressed by its sha256, and
`bind_artifact` writes it without binding it as anything's active config. This item adds a per-job
reference to that store. `start_run`, `start_record`, and `start_crawl` accept an optional
`binaryArtifact` field: a sha256 hex digest naming a `binary` artifact already stored for the caller's
org. `valid_sha256` validates its shape. The dispatch-side gate cannot reuse `artifact_exists` as it stands:
that helper deliberately reads a store error as "not confirmed present" and returns the same
`200 {"exists": false}` a real miss returns, so reused unchanged a transient error would read as a
confirmed miss and yield exactly the 400 this item forbids. So this item extracts the three-state probe (present / confirmed absent / unconfirmed) behind
`artifact_exists`, leaving `artifact_exists` as the thin `GET /api/artifacts/exists` handler that
narrows it back to today's two states. The dispatch gate reads that three-state result directly: a confirmed absent fails the
request with 400 before any job is registered — never a job that fails later, opaquely, once a worker
tries to fetch it — while an unconfirmed check returns a retryable 503 instead, never a 400 asserting
the artifact was never uploaded. `GET /api/artifacts/exists` itself keeps its current two-state
contract — `200 {"exists": false}` for both a confirmed miss and an unconfirmed check — since its
existing dedup callers are safe reading either as "upload it again"; no client behavior changes there.

The reference travels as a new `Job` field, independent of `Job.bundle`. `Job.bundle` stays exactly what
BE-0413 built: the tree an `Upload` binding resolves to. Nothing here changes `state.binding_for`,
`bind_upload_config`, or `remember_org_config_source`. Two jobs naming different artifacts never contend
for the same record, and neither does one job naming an artifact while the org's bound config stays what
it was.

The artifact's storage key is a pure function of the deployment's object-store prefix, the org, the
artifact kind, and the sha256 (`artifact_store_key`, under the org's `uploads/binary/` prefix in
`bajutsu/serve/upload_artifacts.py`). This item treats that key scheme as a stable contract, not an
implementation detail. Take a CI runner with its own bucket access as an example: knowing the
deployment's prefix, its own org, the `binary` kind segment, and the sha256 it computed — all four, not
the digest alone — it can write the artifact's bytes directly to that key, skipping
`POST /api/artifacts/binary` entirely. The dispatch API needs the resulting sha256 alone, never the
transport that put the bytes there. `GET /api/artifacts/exists` still answers whether a given sha256 is
already stored, whichever path wrote it. A caller with its own credentials and all four inputs gets the
same upload-skip it would through the API.

### Unit 2 — Deliver the override to wherever the job runs

At lease, `worker_lease` signs a presigned GET for the override, the same way it already signs
`bundle_urls` (BE-0413) and `baseline_urls` (BE-0160). The lease returns it as one more key,
`binary_url`. The sha256 the job carries is re-validated as a full hex digest before it becomes a
storage key, and that key stays scoped to the leased job's own org — never a value the worker
supplies. When a job carries a `binaryArtifact` and the lease signs no
`binary_url` for it — no object store configured — the worker fails the job immediately, the same
posture BE-0413 already takes when a bundle's lease signs no url (`bajutsu/serve/cli/worker.py`: "job
needs bundle …, but the lease signed no url for it"): say it here rather than failing opaquely at
install time. The worker downloads and hashes it before use, reusing BE-0413's
streamed-download-and-verify path. It then places the bytes the same way a composed `binary` leg
already does: the worker resolves `appPath` from the job's own config the way `materialize_composition`
resolves it — platform-general, so an Android target's `appPath` is covered exactly like an iOS
target's, not iOS alone — and writes through `_place_binary`'s unzip-or-copy branch, under the same
BE-0051 path confinement `validate_bundle_config` gives a composed tree. The write overwrites whatever
an `Upload`'s tree, or a Git checkout, would otherwise have placed there. And it is the first delivery
path a materials-based job — one with no `bundle` at all — has ever had for a binary it does not
already carry on disk.

The worker's workspace outlives the job — `work` is one directory for the worker's whole lifetime — so
placing an override at `appPath` and leaving today's workspace key unchanged would let it contaminate
the next job leased on that worker: one with no override, or one off the same bundle, would start
against it with nothing announcing it. The override therefore participates in the workspace key itself:

| Job | Workspace |
|---|---|
| bundle job, no override | `.bundles/<org>/<bundle id>` — exactly today's key, unchanged |
| bundle job, override X | keyed by `(bundle id, override sha)` — its own tree |
| materials-based job, override X | a directory keyed by the override sha, instead of the worker's shared working directory |
| materials-based job, no override | the worker's shared working directory — exactly today, unchanged |

A job that names no override keeps today's key exactly, so nothing about existing behavior changes;
only a job carrying an override gets a tree of its own. That makes the placement job-scoped by
construction, with no deletion or re-placement step for the worker to get right. This follows
BE-0413's own principle that a binary's identity is a digest of its contents, so two different
binaries are two different trees; it also inherits BE-0413's disk cost, which `docs/self-hosting.md`
already tells an operator to manage by pruning the bundle cache.

A local, single-process `serve` is a different topology: a job with a `file` or Git binding there runs
with `job.cwd` set to the operator's own project directory (`_register_and_dispatch`), so this item
**refuses** `binaryArtifact` there with a clear error instead of overwriting the operator's build
output at `appPath`. Serve owns no workspace to isolate the placement into, so the contamination the
workspace key solves on the worker has no local answer, and mutating an operator's project directory
unannounced is the side effect directive 2 rules out. An operator on a single-process `serve` already
has direct filesystem access and can point `appPath` wherever they want without this field. This keeps
the item scoped to the topology whose problem it exists to solve — the hosted split, where a worker
runs the job and serve owns the workspace.

A 404/410 on the fetch ends the job the way BE-0413 treats a bundle that is not there (`bundle
unavailable`). A hash mismatch is different: BE-0413 classifies it as transient, so the lease lapses
and another attempt can succeed, rather than one truncated download ending the job for good. Either
way, a run never starts against the wrong binary. Nor does it fall back, unannounced, to whatever
`appPath` would otherwise have resolved to. The run's manifest records the overridden sha256 as
provenance, alongside BE-0073's existing bundle provenance, so which binary a job actually installed
stays answerable after the fact.

### Unit 3 — Tests and documentation

The gate covers each seam without a network or a Simulator:

- `start_run` / `start_record` / `start_crawl` refuse a `binaryArtifact` the org's artifact store does
  not hold, before registering a job.
- A transient object-store error during the dispatch gate's existence check on a named
  `binaryArtifact` returns 503 from that gate, not a 400 claiming the artifact was never uploaded.
- `worker_lease` signs `binary_url` for a job carrying a `binaryArtifact`, scoped to the leased job's
  org.
- A job carrying a `binaryArtifact` whose lease signs no `binary_url` fails immediately, the same way
  a bundle job with no signed url does.
- A materials-based job with no `bundle` places the fetched artifact at its config's `appPath` and runs.
- An Android target's override lands at its own `appPath`, the same seam an iOS target uses.
- A `.app` zip-bundle artifact extracts into a directory at `appPath` rather than landing as a zip
  file.
- A job with both a bound `Upload` and a `binaryArtifact` installs the override, not the bound tree's
  own binary.
- Two concurrent jobs naming different artifacts each install their own, and neither changes the org's
  active config binding.
- A job with no `binaryArtifact` that leases after one that had it, on the same worker, runs against
  its own `appPath` binary rather than the leftover — a sequential-on-one-worker failure the existing
  "two concurrent jobs" bullet above does not cover.
- A 404 on the override fetch fails the job, leaving no installed binary behind; a hash mismatch
  instead leaves the lease to lapse, so a retry can succeed instead of the download ending the job
  for good.
- A job that would run in the operator's own bound tree — a single-process `serve` with a `file` or
  Git binding — gets its `binaryArtifact` refused, leaving the operator's `appPath` binary untouched.

`docs/self-hosting.md`, `docs/cli.md`, and their Japanese mirrors gain a paragraph on the
`binaryArtifact` field and what a job's manifest records for it.

## Alternatives considered

| Alternative | Why we did not take it |
|---|---|
| Name the binary by a raw object-storage path (`prefix/org/<path>`), trusted by location alone | Drops content-addressing: the object at that path can change after the fact, so a run's manifest can no longer say which bytes it installed. It also reopens the path-validation surface BE-0413's sha-revalidation and BE-0051's confinement already close, for no capability a sha256 reference does not already give. |
| Extend the per-job override to `config` and `scenarios` too | The motivating gap is binary-specific: CI varies the binary on every run while holding config and scenarios fixed, so the binary is the only leg a caller needs to vary without mutating the binding. Widening scope here would rebuild a compose-time picker at the dispatch layer for a need this item's motivation does not show. |
| Require a rebind (`bind`/`compose`) before every dispatch, as today's two paths do | Makes the org's active config the unit of change: every sessionless CI caller contends for the one deployment fallback binding instead of each getting the binary its own job asked for, and the bind additionally writes the org's remembered configuration, which a member's next session inherits. |
| Add a presigned-PUT upload endpoint for artifacts, as the one supported transport | Not needed to close the motivating gap: `POST /api/artifacts/binary` plus `GET /api/artifacts/exists` already let a caller dedupe and upload today. A presigned-PUT variant would save a round trip through the control plane's own disk for a large binary, but that is a follow-on optimization, not a blocker — this item's dispatch-time contract is the resulting sha256, not how it arrived. |
| Re-place `appPath` from the bundle/Git tree (or delete the leftover) for every job that carries no override | A materials-based job has no source tree to re-place *from*, so that path needs a delete step and a per-topology branch, where keying the workspace makes the isolation structural and needs neither. |

## Progress

> Keep this current as work proceeds. The checklist mirrors the MECE work breakdown in
> *Detailed design* (one box per unit of work); the log records what changed and when
> (oldest first), linking the PRs.

- [ ] Unit 1 — `binaryArtifact` request field, validated and existence-checked, carried on `Job`
      independent of `Job.bundle`.
- [ ] Unit 2 — Sign and deliver the override on the worker topology, refuse it on a local
      single-process `serve`, with provenance recorded on the run's manifest.
- [ ] Unit 3 — Tests for each seam, plus the `self-hosting` / `cli` documentation.

## References

- [BE-0393 — Per-org config memory, restored into each session](../BE-0393-per-org-config-memory/BE-0393-per-org-config-memory.md)
  — defines which binding a bind actually moves: the session's own slot, or the deployment's fallback
  when the caller has none.
- [BE-0413 — Deliver an uploaded app binary to the worker that runs the job](../BE-0413-worker-app-binary-delivery/BE-0413-worker-app-binary-delivery.md)
  — the presigned-GET delivery and download-verify path this item reuses for a standalone artifact.
- [BE-0073 — Upload a config + scenarios + app-binary bundle as a zip and run it from the web UI](../BE-0073-serve-zip-bundle-upload/BE-0073-serve-zip-bundle-upload.md)
  — the run-manifest provenance block this item's overridden sha256 joins.
- [BE-0268 — Upload config, scenarios, and app binary as independent content-addressed artifacts](../BE-0268-composable-upload-artifacts/BE-0268-composable-upload-artifacts.md)
  — the standalone, content-addressed `binary` artifact this item references without binding it.
- [BE-0325 — Reuse the active composition when uploading only the legs that changed](../BE-0325-compose-incremental-artifact-upload/BE-0325-compose-incremental-artifact-upload.md)
  — the compose-time convenience this item's per-job override is a non-mutating alternative to.
- [BE-0160 — Credential-free worker uploads via presigned URLs](../BE-0160-worker-credential-free-uploads/BE-0160-worker-credential-free-uploads.md)
  — the presigned-URL brokering `binary_url` extends.
- [BE-0090 — Govern and sandbox command execution from uploaded bundle configs](../BE-0090-uploaded-config-command-execution/BE-0090-uploaded-config-command-execution.md)
  — the `build:` governance a materials-based job's own binary fetch relies on today, absent this item.
- [BE-0106 — Post-completion worker model](../BE-0106-post-completion-worker-model/BE-0106-post-completion-worker-model.md)
  — the lease protocol `binary_url` joins alongside `bundle_urls` and `baseline_urls`.
