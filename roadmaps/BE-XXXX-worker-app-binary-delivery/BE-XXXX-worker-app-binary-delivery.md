**English** · [日本語](BE-XXXX-worker-app-binary-delivery-ja.md)

# BE-XXXX — Deliver an uploaded app binary to the worker that runs the job

<!-- BE-METADATA -->
| Field | Value |
|---|---|
| Proposal | [BE-XXXX](BE-XXXX-worker-app-binary-delivery.md) |
| Author | [@paihu](https://github.com/paihu) |
| Status | **Implemented** |
| Tracking issue | [Search](https://github.com/bajutsu-e2e/bajutsu/issues?q=is%3Aissue+label%3Aroadmap-tracking+in%3Atitle+"BE-XXXX") |
| Implementing PR | [#1933](https://github.com/bajutsu-e2e/bajutsu/pull/1933) |
| Topic | Hosting the web UI |
<!-- /BE-METADATA -->

## Introduction

A hosted Bajutsu deployment splits one process into two. The control plane serves the web user
interface (UI) and owns the queue. A separate `bajutsu worker` process leases each job over HTTP
(Hypertext Transfer Protocol). The worker runs the job on a machine that can drive the device. The
two processes share no filesystem.

A user opens a configuration by dropping a zip bundle on the web UI. That zip carries a
`bajutsu.config.yaml`, its scenario tree, and a built app binary. The configuration names the binary
in `appPath`. The compose picker offers the same three parts as independent artifacts. Either way,
the control plane extracts the upload into a tree on its own disk and binds the tree.

This item ships that bound tree to the worker that leases the job. The run then finds the binary
where its configuration says the binary lives.

## Motivation

A worker cannot run an uploaded bundle today. The job specification carries the configuration and
the scenario as text, under `materials`. The specification also carries `app_path`, but `app_path`
is a string. Nothing carries the bytes.

The run starts against a path that does not exist on the worker. No on-demand build covers for
that. `_governed_build` nulls an upload binding's `build:` by policy, since Bajutsu takes a prebuilt
app and does not build one, so `_build_app` returns success without building. The error surfaces
later, at install time, far from its cause.

Both upload paths hit the same wall:

| Bind kind | What the control plane holds | What the worker receives today |
|---|---|---|
| Single zip (BE-0073) | The extracted tree, plus the raw zip in object storage | Configuration and scenario text alone |
| Composed triple (BE-0268) | The composed tree, plus each leg in object storage | Configuration and scenario text alone |

**Verifiable outcome.** After this change, an uploaded bundle's job runs on a remote worker, app
installed. A reader can check the difference from the web UI. Dispatch one run against a hosted
deployment whose worker holds no copy of the app.

## Detailed design

The design reuses the mechanism BE-0160 already built for visual baselines. The control plane signs
a URL (uniform resource locator). The worker fetches over plain HTTP, with no cloud credentials of
its own. One presigned GET URL for the bundle zip joins `baseline_urls` in the lease response.

### Unit 1 — One description of a bound upload, for either bind kind

Both bind kinds produce an `Upload` whose `sha256` identifies the bound tree, but they store
different things under it. A single-zip bind holds its whole tree as one object at
`uploads/<sha256>.zip`, beneath the org prefix. A composed bind holds one object per supplied leg
and no whole-tree object at all.

`Upload.worker_ref` names whichever of the two a bind produced: the tree's `id`, the per-leg
`artifacts` shas (None for a single-zip bind), and the display name a single-YAML `scenarios` leg
must land under. One value describes either kind, so the units below branch on its contents rather
than on how the bind happened.

Zipping the composed tree into the single-zip shape would have removed the branch entirely, at a
cost the reviewer was right to weigh: a full copy of the app binary per composition, undoing
BE-0268's per-leg dedup, plus a synchronous multi-hundred-megabyte zip inside the bind request.
Naming the legs instead keeps that dedup and pays nothing at bind time.

### Unit 2 — Carry that description on the job, and sign it at lease

`_register_and_dispatch` is the single tail every dispatcher funnels through. That tail already
freezes the job's working directory from the caller's binding. Unit 2 stamps `Upload.worker_ref`
there too. A new `Job.bundle` field carries it, and `job_spec` serializes it, so the description
reaches a worker through the queue.

`worker_lease` then signs a presigned GET URL per object the description names — one under `bundle`
for a single-zip bind, one per artifact kind for a composed triple. The org comes from the leased
job, never from a worker-supplied value, and every sha is re-validated as a hex digest before it
becomes a storage key. The signed URLs join the response as `bundle_urls`, beside the
`baseline_urls` that already travel the same way.

### Unit 3 — Extract the bundle on the worker, and run the job from its root

The worker downloads what the lease signed. It rebuilds the tree with the control plane's own
functions. A single-zip bind goes through `materialize_bundle`, passed
`validate=validate_bundle_config`. That validator confines every target's paths to the tree
(BE-0051). A composed triple goes through `materialize_composition`, the same assembly the bind
itself ran, which applies the validator too. `find_bundle_config` then locates the configuration
inside the tree, tolerating a zip that wraps everything in one folder. Its parent directory becomes
the workspace for this job.

Running from that root is what makes the rest resolve. The configuration's relative `appPath`,
`scenarios`, and `baselines` entries all point inside the tree. The run reads them with no path
rewriting. The worker loop hands the same root to the console log writer and to the evidence upload,
so one workspace serves the whole job.

The bundle identity keys the tree, so a second job off the same bundle fetches nothing. One
workspace then serves every job off one bundle, and the run writes its `runs/` tree inside it. That
identity is a digest of the contents, never a file name, and that is what keeps two builds apart.
Two bundles whose binaries share a path and differ in bytes are two ids, so each run installs its
own. The runner's `reinstall` precondition already defaults to a clean install from the workspace
the run started in.

Paying a per-job copy of the tree would isolate the `runs/` writes as well. An app binary is too
large to copy per job for that alone. Trees do nest per org, for the reason the control plane's
caches do. The tree is mutable, so one tenant's run evidence must not land in another's directory.
An org id is operator-authored, so two different ids can reduce to one safe segment. Three cases
do it: a stripped character, an id past 64 characters, and a pair differing in case alone on a
case-insensitive filesystem. Each would defeat that isolation. The cache keeps an id as-is when it
is already a safe segment, and gives every other one a digest of the original.

The fetch runs on the run's own background thread, under the same heartbeat. It is the job's largest
transfer. A fetch slower than the lease timeout would otherwise trip a reclaim this worker would
never notice, and it would then run the job beside whichever worker won the re-lease.

Observing that reclaim differs from acting on it in time. A flag checked once the fetch returns
is what stops the run from starting. Without that flag, a fetch finishing right after the reclaim
would still walk the run's own thread into installing the app and driving the device, beside the
worker that won the re-lease. Its *result* would then be discarded, too late to matter. Nothing has
touched the device yet when the fetch returns, so returning there instead costs nothing.

The worker hashes each part once it lands, against the sha256 the job named. A short body is not an
error to `http.client`, so nothing else notices a truncated download. A truncated raw binary reaches
no reader at all. Its corrupt tree then stays cached for every later job off that bundle.

Phase, never exception type, tells the two kinds of trouble apart. A broken *download* — a reset
connection, a `503`, a digest mismatch — posts nothing and leaves the lease to lapse. The queue's
own reclaim-and-retry then gives the job another attempt. One network blip must not surface as a red
run (directive 2).

Everything after the download is deterministic over verified bytes. A break there is permanent, and
the worker reports it. A `404`/`410` counts as permanent too, since the object is not there and no
retry will conjure it. Keying off the type would misfile both directions: `HTTPError` and the
`FileExistsError` a bad tree raises are both `OSError`.

Two consequences follow that an operator should know about. Nothing evicts a tree, so a deployment
that uploads a bundle per build accumulates one tree per build on the worker's disk — the same
property the control plane's own extraction cache has, on the machine that runs the jobs.
`docs/self-hosting.md` says to prune `.bundles/` rather than adding a policy this item cannot size.
And a bundle's run no longer downloads the org's stored baselines, since the bundle ships its own;
a deployment that approves baselines through serve and also uploads bundles will see visual
assertions start comparing against the bundle's `baselines/` instead.

`_get_file` streams to disk instead of reading the whole response into memory. An app binary dwarfs
the baseline images that helper first served.

A bundle also ships its own baselines, and the dispatcher must stop materializing the org's stored
ones over them. `_download_baselines` clears its destination directory first, so with the workspace
now inside the bundle it would delete what the bundle shipped. The dispatcher already omits
`--baselines` for an upload binding, and Unit 3 makes `materialize_baselines` agree.

### Unit 4 — Tests and documentation

The gate covers each seam without a network or a Simulator:

- `worker_lease` signs the whole-tree zip for a single-zip bind, and each leg for a triple.
- `worker_lease` returns `bundle_urls` for a job whose specification carries a bundle identity.
- The worker resolves a downloaded zip to a workspace root, for a flat zip and a wrapped one.
- The worker re-composes a triple from its legs, placing the binary at the config-named `appPath`.
- Two bundles whose binaries share a path but differ in bytes resolve to two workspaces.
- A job with no bundle identity keeps the plain workspace, so a Git-sourced run keeps working.
- A job that carries a bundle identity the lease could not sign fails, rather than running blind.
- A reclaim arriving mid-fetch is seen, so the heartbeat provably covers the download.
- A reclaim seen mid-fetch stops the run before it starts, never merely discards its result.
- Two org ids that reduce to the same cache segment still get separate, non-colliding directories.
- A truncated part and a mismatched leg digest are caught, and leave no tree behind to reuse.
- A `503` on the fetch is retried; a `404`, and a failure raised after the bytes land, are reported.
- `_get_file` writes a body larger than one read to disk, so a bundle never buffers whole in memory.
- An upload binding dispatches with `materialize_baselines` off, leaving the bundle's own in place.

`docs/self-hosting.md` and its Japanese mirror gain a paragraph on what the worker now fetches.

## Alternatives considered

| Alternative | Why we did not take it |
|---|---|
| Ship the binary inside `materials` | `materials` maps a path to text, and a Mach-O binary is not text |
| Zip the composed tree and sign that one object | Stores the app binary once per composition, undoing BE-0268's per-leg dedup |
| Give the worker object-store credentials | Reverses BE-0160, whose whole point is a credential-free worker |
| Require a `build:` command on every hosted [target](../../docs/glossary.md#target-app-device) | Breaks the upload story, whose premise is a prebuilt binary |
| Mount shared storage across the split | Adds an infrastructure requirement the HTTP-only worker avoids today |

Signing the legs does leave the worker with two shapes to handle rather than one. The cost is small
because neither shape is new code: `materialize_bundle` and `materialize_composition` are the
control plane's own functions, and the worker calls whichever the job's `Upload.worker_ref` names.

## Progress

> Keep this current as work proceeds. The checklist mirrors the MECE work breakdown in
> *Detailed design* (one box per unit of work); the log records what changed and when
> (oldest first), linking the PRs.

- [x] Unit 1 — Describe a bound upload once (`Upload.worker_ref`), for either bind kind.
- [x] Unit 2 — Carry that description on the job, and sign `bundle_urls` at lease.
- [x] Unit 3 — Rebuild the bundle on the worker, and run the job from its root.
- [x] Unit 4 — Tests for each seam, plus the self-hosting documentation.

## References

- [BE-0073 — Upload a config + scenarios + app-binary bundle as a zip](../BE-0073-serve-zip-bundle-upload/BE-0073-serve-zip-bundle-upload.md)
  — the single-zip bind whose binary this item delivers.
- [BE-0243 — Persist uploaded zip config bundles to object storage](../BE-0243-upload-bundle-durable-storage/BE-0243-upload-bundle-durable-storage.md)
  — the `uploads/<sha256>.zip` key this item signs.
- [BE-0268 — Upload config, scenarios, and app binary as independent artifacts](../BE-0268-composable-upload-artifacts/BE-0268-composable-upload-artifacts.md)
  — the composed bind Unit 1 describes leg by leg.
- [BE-0160 — Credential-free worker uploads via presigned URLs](../BE-0160-worker-credential-free-uploads/BE-0160-worker-credential-free-uploads.md)
  — the presigned-URL seam this item extends.
- [BE-0106 — Post-completion worker model](../BE-0106-post-completion-worker-model/BE-0106-post-completion-worker-model.md)
  — the lease protocol the `bundle_urls` field joins.
