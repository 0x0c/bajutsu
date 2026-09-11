**English** · [日本語](BE-0417-scenario-result-folder-naming-ja.md)

# BE-0417 — Name a scenario's evidence directory after its source file

<!-- BE-METADATA -->
| Field | Value |
|---|---|
| Proposal | [BE-0417](BE-0417-scenario-result-folder-naming.md) |
| Author | [@0x0c](https://github.com/0x0c) |
| Status | **Proposal** |
| Tracking issue | [Search](https://github.com/bajutsu-e2e/bajutsu/issues?q=is%3Aissue+label%3Aroadmap-tracking+in%3Atitle+"BE-0417") |
| Topic | Codebase quality & technical debt |
| Related | [BE-0200](../BE-0200-run-id-contract/BE-0200-run-id-contract.md) |
<!-- /BE-METADATA -->

## Introduction

Inside `runs/<runId>/`, each scenario's evidence lives under its own `sid` directory,
`f"{i:02d}-{scenario_slug(s.name)}"` — a run-order index plus a slug of the scenario's internal
`name:` field ([`bajutsu/common/runner/pipeline.py:269`](../../bajutsu/common/runner/pipeline.py)).
This item changes the slug half of that name from the scenario's `name:` field to the stem (the file
name without its `.yaml` extension) of the file the scenario was actually loaded from, so `sid`
reads, e.g., `00-login_flow` instead of `00-login-succeeds-with-a-valid-password`. The `{i:02d}-`
index prefix is unchanged.

### Not doing

- **The top-level run directory (`runs/<runId>/`, a UTC timestamp) is unchanged.** Its
  lexicographic-sort-equals-chronological-order contract
  ([BE-0200](../BE-0200-run-id-contract/BE-0200-run-id-contract.md)) is relied on by
  `bajutsu/analysis/trace.py`'s `latest_run()`, `serve`'s run and crawl listings
  (`bajutsu/serve/helpers.py`), and `run/notify`'s prior-verdict lookup — none of that changes here.
  Renaming the run directory itself after a scenario file also has no coherent answer for a
  multi-scenario or multi-file run: a `runs/<runId>/` holds `manifest.json` /
  `junit.xml` / `ctrf.json` / `report.html` for every scenario the run executed, not one.
- **No new duplicate-suffix counter is introduced.** The existing `{i:02d}-` index prefix already
  guarantees a unique `sid` within one run, so two scenarios landing on the same file-derived name —
  two files sharing a stem, or one file's `scenarios:` list holding more than one scenario — never
  collide; see *Detailed design* and *Alternatives considered*.
- **A `Scenario` with no known source file keeps today's behavior.** `scenario_slug(s.name)` stays
  as the fallback for a scenario built directly in memory, outside the file loaders (test fixtures,
  for instance) — unaffected by this item.
- **The `--browsers` cross-browser matrix's `<engine>/<sid>/` layer is unchanged.** Only what `sid`
  itself is built from changes.
- **The pre-existing name-keyed collision in `_matrix()`** (`bajutsu/common/report/manifest.py:78-91`
  builds the `--browsers` matrix summary keyed by scenario name, so two same-named scenarios in one
  engine overwrite each other's matrix cell) is a separate, already-existing issue this item does not
  touch.

## Motivation

`sid`'s slug comes from the scenario's internal `name:` field today, not from the file the scenario
was authored in. `name:` is free-form prose and need not resemble the file's own name: a scenario
authored in `login_flow.yaml` can carry `name: "Login succeeds with a valid password"`, which slugs
to `00-login-succeeds-with-a-valid-password`. Finding one scenario's results back out of
`runs/<runId>/` then means opening `manifest.json` and matching its `scenario` field against the file
an operator actually has in mind — there is no way to go from `login_flow.yaml` straight to the
directory holding its evidence. That friction is the request behind this item: locating a specific
scenario's own results among several is harder than it needs to be, particularly when re-running the
same scenario file repeatedly while authoring it or chasing a CI failure. Naming `sid`'s slug after
the scenario's own file instead lets an operator go from the file they already know to the directory
that holds its evidence, with no detour through `manifest.json`.

## Detailed design

1. **`Scenario.source_stem`** (new) — a private, load-time-only attribute on
   [`Scenario`](../../bajutsu/common/scenario/models/scenario/scenario.py)
   (`_source_stem: str | None = PrivateAttr(default=None)`) plus a read-only `source_stem` property
   exposing it. A `PrivateAttr` rather than an ordinary field: it is derived provenance the loader
   fills in after parsing, never something a scenario's own YAML declares, and it must never appear
   in `model_dump()` — leaking into a re-serialized scenario file (as `record`, `audit`, or a future
   scenario-editing feature might produce) would turn a load-time detail into part of the scenario's
   authored schema.
2. **The two device-free loaders that read a scenario from a file set it.** Both set
   `source_stem` on the *final* expanded `list[Scenario]`, right before returning — after
   `expand_data`'s per-CSV-row copies already exist, so every row a data-driven scenario expands into
   carries the same source stem:
   - `_expand_file()` in [`bajutsu/run/cli.py:161-200`](../../bajutsu/run/cli.py) — `run`'s own
     setup-prefixing loader.
   - `load_expanded_scenarios()` in
     [`bajutsu/common/scenario/load_expanded.py:63-89`](../../bajutsu/common/scenario/load_expanded.py) —
     shared by `audit`, `trace --explain`, `coverage`, and the serve Web UI's coverage view (and, via
     `load_scenarios_dir()`, by any device-free reader of a whole suite).
3. **`_ScenarioRunner.run_one`'s `sid` construction reads it, through a narrow sanitizer, with a
   fallback.** The two sites —
   [`bajutsu/common/runner/pipeline.py:269`](../../bajutsu/common/runner/pipeline.py) and `:1173`
   (the cross-browser matrix's `_cancelled_pass`) — change from
   `sid = f"{i:02d}-{scenario_slug(s.name)}"` to
   `sid = f"{i:02d}-{sanitize_source_stem(s.source_stem) if s.source_stem else scenario_slug(s.name)}"`.
   `sid` is not only a filesystem path segment: `report.html`'s `src=` / `href=` asset links
   ([`bajutsu/templates/report.html.j2:32,43,47`](../../bajutsu/templates/report.html.j2)) and serve's
   `/runs/<runId>/<sid>/…` fetches interpolate it unescaped, so a raw stem such as `login#1` or `a?b`
   would silently truncate every relative link at the `#` / `?` — a class of breakage
   `scenario_slug()`'s `[0-9a-z-]+` output makes impossible today (see *Alternatives considered*).
   **`sanitize_source_stem()`** (new, beside `scenario_slug()` in
   [`bajutsu/common/orchestrator/types/_functions.py`](../../bajutsu/common/orchestrator/types/_functions.py))
   replaces only characters unsafe in an unescaped HTML attribute or URL path segment — anything
   outside `[A-Za-z0-9_.-]` — with `_`, leaving a plain stem such as `login_flow` unchanged. Unlike
   `scenario_slug()`, it leaves `_` and `.` alone, so `sid` still reads identically to the source
   file's name in the common case; only a stem carrying an unsafe character is altered. The
   `{i:02d}-` prefix stays exactly as it is today, so `sid` stays unique within one run without any
   new counter.
4. **Docs.** [`docs/reporting.md`](../../docs/reporting.md) / [`docs/ja/reporting.md`](../../docs/ja/reporting.md)'s
   "Output layout" section gains a line naming `sid`'s derivation (the source file's stem, or the
   scenario's `name:` field when no source file is known) beside the `runId` format it names today
   (`docs/reporting.md:30-32`), and its layout tree gains the `<sid>/` level it omits today, which
   currently hangs `<stepId>/` directly off `runs/<runId>/`.
5. **Tests.**
   - `tests/runner/test_pipeline.py`: a file-loaded scenario's `sid` uses the source file's stem; a
     `Scenario` built directly (no `source_stem` set) keeps today's `scenario_slug(s.name)` `sid`.
   - A loader-level test for each of unit 2's two loaders, asserting `source_stem` matches the loaded
     file's stem, including the data-driven-expansion case (every expanded row carries the same
     stem).
   - A test that `source_stem` never appears in `Scenario.model_dump()` output.
   - A unit test for `sanitize_source_stem()`: a plain stem such as `login_flow` passes through
     unchanged; a stem carrying an HTML/URL-unsafe character (`login#1`, `a?b`) comes back with only
     that character replaced.

## Alternatives considered

| Alternative | Why we did not take it |
|---|---|
| Rename the top-level run directory (`runs/<runId>/`) itself after the scenario file | Breaks the lexicographic-sort-equals-chronological-order contract [BE-0200](../BE-0200-run-id-contract/BE-0200-run-id-contract.md) established, relied on by `latest_run()`, `serve`'s run/crawl listings, and `run/notify`'s prior-verdict lookup — a replacement for all of that would be needed. It also has no coherent answer for a run that executes more than one scenario or scenario file, since one `runs/<runId>/` directory would need one name for every scenario it holds. |
| Drop the `{i:02d}-` index prefix and rely on a duplicate-suffix counter for uniqueness | The prefix already makes `sid` unique within a run at no extra cost, and keeping it means a directory listing still shows run order at a glance, which a bare counter loses. It does not, however, make same-file scenarios any more identifiable than a counter would: under this item's own design, two scenarios in one `login_flow.yaml` become `00-login_flow` and `01-login_flow`, distinguished only by the same run-order index a `login_flow` / `login_flow_2` counter would carry just as well. `scenario_slug(s.name)` — today's behavior, and this item's fallback when no source file is known — is what actually tells same-file scenarios apart by name, a property neither the index prefix nor a duplicate counter provides on its own. |
| Normalize the file stem through the existing `scenario_slug()` sanitizer | Would turn `login_flow.yaml` into `login-flow`, no longer identical to the file name for the common case — defeating the point of naming `sid` after the file. `sanitize_source_stem()` (see *Detailed design*) gets the same filesystem/HTML/URL safety at a narrower cost, by leaving `_` and `.` untouched. |
| Use the source stem completely raw, with no sanitization | A scenario file's name is already a valid filesystem path segment, but `sid` also travels unescaped into `report.html`'s asset links and serve's `/runs/<runId>/<sid>/…` routes (see *Detailed design*). An unsanitized stem such as `login#1` or `a?b.yaml` would silently truncate those links at the `#` / `?`, with nothing in `make check` catching it. `sanitize_source_stem()` closes that gap while keeping the common case (`login_flow`) unchanged. |
| Thread a parallel `list[str]` of source stems alongside `list[Scenario]` through `run_all` / `run_and_report` / `run_matrix_and_report` and their callers, instead of attaching the stem to `Scenario` | Touches every call site that carries a `list[Scenario]` today — `bajutsu/run/cli.py`, `bajutsu/analysis/cli/audit.py`, and the pipeline test suite — for data that only ever travels with its scenario. A private, load-time-only field on `Scenario` keeps the change local to the two loaders and the one read site. |

## Progress

> Keep this current as work proceeds. The checklist mirrors the MECE work breakdown in
> *Detailed design* (one box per unit of work); the log records what changed and when
> (oldest first), linking the PRs.

- [ ] Not started.

## References

- [BE-0200 — Make the run-id format a single named contract](../BE-0200-run-id-contract/BE-0200-run-id-contract.md)
- [`bajutsu/common/scenario/models/scenario/scenario.py`](../../bajutsu/common/scenario/models/scenario/scenario.py)
- [`bajutsu/common/scenario/load_expanded.py`](../../bajutsu/common/scenario/load_expanded.py)
- [`bajutsu/run/cli.py`](../../bajutsu/run/cli.py)
- [`bajutsu/common/runner/pipeline.py`](../../bajutsu/common/runner/pipeline.py)
- [`bajutsu/common/orchestrator/types/_functions.py`](../../bajutsu/common/orchestrator/types/_functions.py)
- [`bajutsu/templates/report.html.j2`](../../bajutsu/templates/report.html.j2)
- [`docs/reporting.md`](../../docs/reporting.md)
