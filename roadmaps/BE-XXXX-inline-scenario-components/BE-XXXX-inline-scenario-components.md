**English** · [日本語](BE-XXXX-inline-scenario-components-ja.md)

# BE-XXXX — Inline, scenario-local components

<!-- BE-METADATA -->
| Field | Value |
|---|---|
| Proposal | [BE-XXXX](BE-XXXX-inline-scenario-components.md) |
| Author | [@0x0c](https://github.com/0x0c) |
| Status | **Proposal** |
| Tracking issue | [Search](https://github.com/bajutsu-e2e/bajutsu/issues?q=is%3Aissue+label%3Aroadmap-tracking+in%3Atitle+"BE-XXXX") |
| Topic | Scenario authoring features |
<!-- /BE-METADATA -->

## Introduction

Let a scenario file declare an inline `components:` block. Each entry maps a name to a BE-0030
component: a reusable, parameterized step sequence, scoped to that one file. A `use: { component:
<name> }` step in the same file resolves the name directly. A step block reused inside a single
file then needs no separate component file. BE-0030's cross-file `use: { component: <path> }` keeps
working unchanged and still owns reuse that spans a suite.

## Motivation

BE-0030 defines a *component*: a reusable, parameterized sequence of steps. A `use` step expands it
into the caller's step list before the run. A component always lives in its own file: a `use: {
component: <path> }` step resolves that path. Extracting even a short, three-step block needs a new
file, a name for it, and a wired relative path all the same. That fixed cost falls on every
extraction. It applies whether the resulting component ends up called from one scenario file or
from every file in the suite.

That cost is not proportional to the reuse it buys when the reuse stays inside one file. A file that
defines two or three related scenarios often repeats one short step block across those scenarios and
nowhere else — a search box tried with different queries, a form submitted with different field
combinations. Splitting that block into its own file adds a file a reader must open to see what a
`use` step does, for a component called from a single file. An author facing that trade instead
repeats the steps by hand in each scenario: the same duplication BE-0030 already set out to remove
for the cross-file case.

An inline, file-scoped `components:` block removes that trade for the local case. An author defines
the component next to the scenarios that call it, in the same file. No new entry is needed in the
suite's directory listing for a name that a single file ever uses. Take a scenario file that defines
a component under `components:` and calls it with `use: { component: <name> }` from two scenarios in
that file. At load time it expands to the same step list a hand-duplicated version would produce.
Reading the expanded steps with `bajutsu trace --explain` confirms it, and no second file appears
for the reuse.

## Detailed design

A file-scoped sibling of BE-0030's file-based component. It resolves through the same `use` step and
the same `expand_components` macro (`bajutsu/common/scenario/expand.py`). The run loop still sees
plain, fully-expanded steps alone, so determinism holds.

- **A new `components:` field on the scenario file.** `ScenarioFile`
  (`bajutsu/common/scenario/models/scenario/scenario_file.py`) gains `components: dict[str,
  Component]`, defaulting to empty. Each entry is the same `Component` model BE-0030 already
  validates a standalone component file against (`params` + `steps`). One schema serves both
  forms.
- **A name resolves locally first; a path resolves as a file; the two never collide.** `use: {
  component: <ref> }` keeps a single field. The ref's own shape decides how it resolves. A ref
  containing `/` or ending in `.yaml` / `.yml` resolves as a file, the same way BE-0030 already
  resolves it. A bare name with neither marker looks up that key in the current file's own
  `components:` map instead. The two forms read as distinct on sight, so a scenario file's
  file-scoped names and a suite's file-based components share the `use` step. This needs neither a
  new field nor a naming convention.
- **The lookup stays inside `load_expanded.py`'s `resolve` closure.** `expand_components`'s `resolve:
  Callable[[str], Component]` parameter keeps its existing signature. `load_expanded_scenarios`
  (`bajutsu/common/scenario/load_expanded.py`) wraps it: the wrapper checks the loaded file's own
  `components:` map first, then falls back to `contained_ref` + `load_component` for a path-shaped
  ref. `expand_components`'s recursion, cycle check, missing/unknown-param check, and depth limit
  already apply uniformly to whatever `resolve` returns. A file-scoped component can `use` a
  file-based one, or another file-scoped one, with no new code path either way.
- **No new path-containment surface.** The loader parses a file-scoped component once, as part of
  the scenario file it already read. Resolving its name never opens a second file, so BE-0174's
  containment check has nothing new to guard here.
- **Scoped to one file, as agreed.** The loader reads `components:` per file. It never merges the
  map across a suite directory's other files (`load_scenarios_dir` loads each file independently),
  so a name declared in one file stays invisible to another. Reuse across files stays BE-0030's
  file-ref job.

```yaml
# one scenario file — no separate component file
components:
  search:
    params: [query]
    steps:
      - type: { text: "${params.query}", into: { id: home.search }, submit: true }

scenarios:
  - name: search returns dogs
    steps:
      - use: { component: search, with: { query: dog } }
    expect:
      - label: { sel: { id: home.status }, equals: "1 result" }
  - name: search returns cats
    steps:
      - use: { component: search, with: { query: cat } }
    expect:
      - label: { sel: { id: home.status }, equals: "2 results" }
```

## Alternatives considered

* **A suite-wide implicit registry (bare names searched across every file).** Rejected: the user
  confirmed the reuse this item targets stays inside one file. Searching a whole suite for a bare
  name would blur that boundary back into BE-0030's cross-file job. It would also reopen the
  path-containment question BE-0174 exists to close, for a case a real file already answers.
* **YAML anchors / merge keys for in-file reuse.** Rejected for the same reason BE-0030 rejected them
  for cross-file reuse. An anchor cannot take a named, validated argument the way `with:` binds
  `params`, so a caller cannot vary the reused block per call site without hand-editing the expanded
  text.
* **A distinguishing syntax on `use` (for example `component: "local:<name>"`).** Rejected in favor
  of deciding by the ref's own shape: a path-like ref versus a bare name. Every existing file ref in
  this repository's scenarios already ends in `.yaml` / `.yml`. The shape rule needs no new syntax
  on `use`, and no scenario written before this change needs an update.

## Progress

> Keep this current as work proceeds. The checklist mirrors the MECE work breakdown in
> *Detailed design* (one box per unit of work); the log records what changed and when
> (oldest first), linking the PRs.

- [ ] Add `components: dict[str, Component]` to `ScenarioFile`
- [ ] Resolve a `use` ref by shape (bare name → the file's own `components:` map; path-like ref →
      the existing file resolution) inside `load_expanded_scenarios`'s `resolve` closure
- [ ] Cover it in the fast suite:
      - A file-scoped component expands identically to its hand-duplicated steps.
      - A file-scoped component and a file-based component coexist in one scenario.
      - A bare name undefined in `components:` fails with a clear error.
      - A file-scoped component's name stays invisible from a sibling file in the same suite
        directory.
      - A file-scoped component may itself `use` a file-based component, and the reverse.
- [ ] Update `docs/scenarios.md` (§Components) and `docs/dsl-grammar.md` (§6.2) plus their `docs/ja/`
      mirrors

## References

`bajutsu/common/scenario/models/scenario/component.py`, `bajutsu/common/scenario/expand.py`,
`bajutsu/common/scenario/load_expanded.py` — the component model and the `use` expansion this item
extends.

[BE-0030 — Parameterized shared steps](../BE-0030-parameterized-shared-steps/BE-0030-parameterized-shared-steps.md) —
the file-based component this item adds a scenario-local sibling to.

[BE-0174 — Contain scenario component and data refs within the suite root](../BE-0174-scenario-ref-path-containment/BE-0174-scenario-ref-path-containment.md) —
the containment guarantee a file-scoped component needs no change to, since it never opens a second
file.

[docs/scenarios.md](../../docs/scenarios.md#components-use--reusable-steps),
[docs/dsl-grammar.md](../../docs/dsl-grammar.md#62-components-use--reusable-steps) — the authoring
and normative docs this item updates.
