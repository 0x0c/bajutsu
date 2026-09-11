**English** · [日本語](BE-XXXX-scenario-slug-length-cap-ja.md)

# BE-XXXX — Cap scenario evidence-directory slug length

<!-- BE-METADATA -->
| Field | Value |
|---|---|
| Proposal | [BE-XXXX](BE-XXXX-scenario-slug-length-cap.md) |
| Author | [@0x0c](https://github.com/0x0c) |
| Status | **Proposal** |
| Tracking issue | [Search](https://github.com/bajutsu-e2e/bajutsu/issues?q=is%3Aissue+label%3Aroadmap-tracking+in%3Atitle+"BE-XXXX") |
| Topic | Codebase quality & technical debt |
| Related | [BE-0417](../BE-0417-scenario-result-folder-naming/BE-0417-scenario-result-folder-naming.md), [BE-0031](../BE-0031-data-driven-scenarios/BE-0031-data-driven-scenarios.md) |
<!-- /BE-METADATA -->

## Introduction

Bajutsu writes each scenario's evidence under `runs/<runId>/<sid>/`. `sid` combines a two-digit
run-order index with a slug from
[`scenario_slug()`](../../bajutsu/common/orchestrator/types/_functions.py). `scenario_slug()`
reduces the scenario's `name` field to `[0-9a-z-]` characters, but caps nothing. A long `name`
produces an arbitrarily long slug. This item adds a fixed length cap to `scenario_slug()`'s
output. The function now truncates an oversized slug instead of letting it grow without bound.
The evidence directory then stays under a safe length, regardless of the scenario's name.

### Not doing

- **The top-level run directory (`runs/<runId>/`, a UTC timestamp) is unchanged.** This item
  touches the per-scenario slug nested under it, alone.
- **`Scenario.name` itself stays untruncated.** Every other reader of the full name —
  `manifest.json`'s `scenario` field, `report.html`, and `declared_name()`'s row-suffix matching
  for serve's run pickers ([`bajutsu/common/scenario/expand.py:117`](../../bajutsu/common/scenario/expand.py)) —
  keeps reading the name in full. This item caps the derived filesystem slug alone.
- **No new duplicate-suffix counter.** Every `sid` a run writes carries the `{i:02d}-` index
  prefix, which keeps it unique within that run, truncated slug or not.
  [BE-0417](../BE-0417-scenario-result-folder-naming/BE-0417-scenario-result-folder-naming.md)
  gives the same reasoning for leaving that prefix alone. Two fallbacks build a bare slug with no
  prefix — `scenario_slug(scenario.name)` when a direct `run_scenario` caller passes no
  `scenario_id` ([`bajutsu/common/orchestrator/loop/_functions.py:645`](../../bajutsu/common/orchestrator/loop/_functions.py)),
  and `scenario_slug(r.scenario)` for a `sid`-less result in the report matrix
  ([`bajutsu/common/report/manifest.py:127`](../../bajutsu/common/report/manifest.py)) — and can
  collide after truncation where they do not today. Neither sits on the path a run takes
  (`pipeline.py:782` always passes `scenario_id=sid`, and `pipeline.py:820` stamps
  `result.sid = sid`), so this item leaves both unchanged.
- **BE-0417's own naming change is untouched.** BE-0417 is a separate, still-unimplemented item.
  It derives a file-loaded scenario's slug from a source-file stem instead of `name`, through a
  new `sanitize_source_stem()` function. This item caps the length of the slug `scenario_slug()`
  produces today; it takes no position on which field that slug derives from. If BE-0417 lands,
  giving `sanitize_source_stem()` the same cap is that item's own implementer's job.

## Motivation

Data-driven scenarios
([BE-0031](../BE-0031-data-driven-scenarios/BE-0031-data-driven-scenarios.md)) run one scenario
per CSV row. `_row_name()`
([`bajutsu/common/scenario/expand.py:102`](../../bajutsu/common/scenario/expand.py)) builds each
row's `name` by appending every column as a `key=value` pair:

```
{scenario_name} [row {i}: k1=v1, k2=v2, ...]
```

A row with many columns, or one column carrying a long value, produces an oversized `name`.
`scenario_slug()` turns that into an oversized `sid`, and creating the directory fails.

An operator hits this by running the same scenario across several parameter combinations. That is
the case data-driven scenarios exist for in the first place. The run then breaks on a step
unrelated to the scenario's own logic.

Capping `scenario_slug()`'s output fixes this at a single choke point. Every call site that builds
a `sid` goes through that one function:

- [`bajutsu/common/runner/pipeline.py:270`](../../bajutsu/common/runner/pipeline.py) and `:1239`
- [`bajutsu/common/report/manifest.py:127`](../../bajutsu/common/report/manifest.py)
- [`bajutsu/common/orchestrator/loop/_functions.py:645`](../../bajutsu/common/orchestrator/loop/_functions.py)

One change to `scenario_slug()` covers all four call sites. Nothing here needs special-casing for
the data-driven case.

A head-preserving cut has one accepted consequence. Once a scenario's own name alone approaches
`_MAX_SLUG_LENGTH`, every row of the same run can share an identical slug. The row-distinguishing
`key=value` suffix `_row_name()` appends lands past the cut. The `{i:02d}-` index prefix still
tells the directories apart — the same guarantee *Not doing* relies on for the two bare-slug
fallbacks. This trades away which characters of the slug an operator sees, not the write's
success.

Once this item lands, a data-driven scenario with long CSV column values runs to completion. It
writes its evidence directory instead of failing to create one, as it does today.

## Detailed design

1. **A length cap inside `scenario_slug()`.** Add `_MAX_SLUG_LENGTH = 60` beside the function in
   [`bajutsu/common/orchestrator/types/_functions.py`](../../bajutsu/common/orchestrator/types/_functions.py).
   The existing regex already collapses each run of non-alphanumeric characters to `-`, strips the
   result, and lowercases it. Slice that result to `_MAX_SLUG_LENGTH` characters next, then call
   `.rstrip("-")` to drop a hyphen the cut may leave dangling. Fall back to `"scenario"` when that
   leaves nothing — the function already returns that same fallback for an all-symbol name. The
   function reduces its input to `[0-9a-z-]` first, so slicing by character count needs no
   multibyte-boundary handling: every character in the output is one byte. `_MAX_SLUG_LENGTH = 60`
   sits comfortably under every filesystem limit this project has to consider. Common filesystems
   cap a filename component at 255 bytes; an encrypted home directory (eCryptfs) narrows that to
   roughly 143. Sixty stays well under either, and short enough to scan in a directory listing. It
   renames the evidence directory of any scenario whose slug is 61 characters or longer today. That
   scenario keeps running; the rename touches only its `sid`.
2. **No other call site changes.** `scenario_slug()` is the one function every `sid`-building call
   site shares (see *Motivation*'s four sites). The cap reaches every one of them without any
   further edits.
3. **Docs.** [`docs/reporting.md`](../../docs/reporting.md) /
   [`docs/ja/reporting.md`](../../docs/ja/reporting.md) gain a short paragraph beside the existing
   `runId` / `stepId` line, naming `sid`'s derivation (a run-order index plus a name-derived slug)
   and the new cap.
4. **Tests.**
   - A unit test for `scenario_slug()`: an overlong name comes back capped, with no trailing
     hyphen.
   - A unit test reproducing the reported case: a long CSV row produces a capped `sid`.
   - A test that colliding truncated slugs still land in distinct directories, via the existing
     `{i:02d}-` index prefix.

## Alternatives considered

| Alternative | Why we did not take it |
|---|---|
| Refuse a scenario whose slug would exceed the cap, mirroring [BE-0404](../BE-0404-collapse-project-layer/BE-0404-collapse-project-layer.md)'s "refuse, don't truncate" rule for run-history labels (`MAX_LABEL_LENGTH`, `bajutsu/common/report/manifest.py:13`) | A run-history label is text an operator typed and expects preserved exactly. Refusing it hands control back to the operator. `sid`'s slug is a derived filesystem id nobody authors directly — for a data-driven scenario, it comes from CSV values an operator may not control row by row. Refusing to run over one long parameter value blocks the whole scenario file, where a legible, truncated slug does not. |
| Hash the slug to a fixed-length digest instead of truncating it | A digest carries none of the original name, defeating the reason `scenario_slug()` derives the directory name from the scenario in the first place: letting an operator recognize a result by eye. Truncation keeps the recognizable lead of the name. |
| Truncate `Scenario.name` itself, before `scenario_slug()` runs | `name` also feeds `manifest.json`'s `scenario` field, `report.html`, and `declared_name()`'s row-suffix matching for serve's run pickers. Truncating it there would lose information those consumers need. `sid` is the only consumer that is purely a filesystem identifier, so it is the only one this item caps. |
| Make the cap configurable per target | The cap protects a filesystem write, not app behavior. The app-agnostic boundary (prime directive 3) puts per-app differences in config, not a filesystem constant that holds the same regardless of the target under test. |
| Keep the row-distinguishing suffix instead of the scenario name's own lead — truncate from the front, or elide the middle (a head fragment plus a tail fragment) | The scenario's own name is what an operator recognizes on sight, for a data-driven scenario and an ordinary one alike; the `key=value` suffix `_row_name()` appends is useful only in the data-driven case, and the `{i:02d}-` index prefix already keeps that case's rows distinguishable by run order. Keeping the head trades away the suffix, not the name. A head-and-tail elision would restore the suffix, at the cost of a second slice, a wider test matrix, and a slug that no longer reads as one continuous name at a glance. |

## Progress

> Keep this current as work proceeds. The checklist mirrors the MECE work breakdown in
> *Detailed design* (one box per unit of work); the log records what changed and when
> (oldest first), linking the PRs.

- [ ] Not started.

## References

- [BE-0417 — Name a scenario's evidence directory after its source file](../BE-0417-scenario-result-folder-naming/BE-0417-scenario-result-folder-naming.md)
- [BE-0031 — Data-driven scenarios](../BE-0031-data-driven-scenarios/BE-0031-data-driven-scenarios.md)
- [BE-0404 — Collapse the project layer](../BE-0404-collapse-project-layer/BE-0404-collapse-project-layer.md)
- [`bajutsu/common/orchestrator/types/_functions.py`](../../bajutsu/common/orchestrator/types/_functions.py)
- [`bajutsu/common/scenario/expand.py`](../../bajutsu/common/scenario/expand.py)
- [`bajutsu/common/runner/pipeline.py`](../../bajutsu/common/runner/pipeline.py)
- [`bajutsu/common/report/manifest.py`](../../bajutsu/common/report/manifest.py)
- [`bajutsu/common/orchestrator/loop/_functions.py`](../../bajutsu/common/orchestrator/loop/_functions.py)
- [`docs/reporting.md`](../../docs/reporting.md)
