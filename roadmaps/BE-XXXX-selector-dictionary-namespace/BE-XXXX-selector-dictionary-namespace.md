**English** · [日本語](BE-XXXX-selector-dictionary-namespace-ja.md)

# BE-XXXX — A named selector dictionary: define an element once, reference it everywhere

<!-- BE-METADATA -->
| Field | Value |
|---|---|
| Proposal | [BE-XXXX](BE-XXXX-selector-dictionary-namespace.md) |
| Author | [@0x0c](https://github.com/0x0c) |
| Status | **Proposal** |
| Tracking issue | [Search](https://github.com/bajutsu-e2e/bajutsu/issues?q=is%3Aissue+label%3Aroadmap-tracking+in%3Atitle+"BE-XXXX") |
| Topic | Scenario authoring features |
| Related | [BE-0033](../BE-0033-scenario-variables-control-flow/BE-0033-scenario-variables-control-flow.md), [BE-0023](../BE-0023-self-healing-guards/BE-0023-self-healing-guards.md), [BE-0174](../BE-0174-scenario-ref-path-containment/BE-0174-scenario-ref-path-containment.md), [BE-0119](../BE-0119-scenario-schema-versioning/BE-0119-scenario-schema-versioning.md), [BE-0261](../BE-0261-serve-author-yaml-roundtrip/BE-0261-serve-author-yaml-roundtrip.md), [BE-0050](../BE-0050-e2e-coverage-map/BE-0050-e2e-coverage-map.md), [BE-0321](../BE-0321-test-impact-analysis/BE-0321-test-impact-analysis.md) |
<!-- /BE-METADATA -->

## Introduction

A scenario names an element by repeating its selector at every use. `components`
(`bajutsu/common/scenario/models/scenario.py:294`) factor out a *sequence of steps*, and `${params.*}`
substitutes into any string field — but neither gives a name to a *selector*. This item adds a
dictionary of named selectors, expanded at load time exactly as components are, so the runner and
every static analysis see the resolved selector and learn nothing new.

## Motivation

In the showcase suite, `id: search.field` is written 25 times across 9 files, and `id: log.submit`
13 times. Every one of those is a copy of the same fact — *this is the search field* — and when the
application renames the identifier, all 25 must change together or the suite half-breaks.

That is not only tedious; it defeats a mechanism the repository already built. `triage`'s
deterministic self-heal proposes a `renameId` fix, and `apply_fix`
(`bajutsu/triage/heuristic.py:170`) replaces the identifier as a whole token — but `_apply_fix`
(`bajutsu/triage/cli.py:292`) reads, patches, and writes **one file**: the scenario that failed. An
identifier spread over nine files gets one of them fixed. The rename is correct and incomplete, and
the incompleteness is invisible until the next run fails somewhere else.

The gap is narrow and worth stating precisely, because a reader may reasonably think the grammar
already covers it. It nearly does: `_interp_steps` (`bajutsu/common/scenario/expand.py:17`)
substitutes bindings through a `model_dump` round-trip, so `${params.x}` can carry an **id string**
into a selector. What it cannot carry is a **selector** — a mapping with `traits`, `within`, or
`index`. So today a shared name is available for the simplest case only, and only by wrapping every
use in a component, which forces a step where the author wanted an expression.

Once this ships, a reader can check it against the showcase suite: the search field is defined once,
each of the 25 sites references that name, and a rename is a one-line edit that `triage --write`
can complete in the single file that holds the definition. `bajutsu coverage` reports the same
identifiers as before, because expansion happens before it looks.

## Detailed design

### The dictionary, and where it lives

A file of named selectors, a mapping from name to the existing `Selector`:

```yaml
# selectors/search.yaml
field: { id: search.field }
count: { id: search.count }
firstRow: { id: stable.row.1 }
```

A scenario file references it with a file-level key, alongside `schema` and `description`:

```yaml
schema: 1
selectors: [selectors/search.yaml, selectors/log.yaml]
scenarios: [...]
```

The reference is a path resolved through `contained_ref`
(`bajutsu/common/scenario/load_expanded.py:21`), so a dictionary cannot reach outside the suite
root — the same containment
[BE-0174](../BE-0174-scenario-ref-path-containment/BE-0174-scenario-ref-path-containment.md)
established for `use:` and `dataFile:`, reused rather than re-derived. A name is `<file stem>.<key>`,
so the example above defines `search.field` and `search.count`; two dictionaries cannot collide
silently, and a duplicate key within one file is a load error.

### The reference, and why it merges with nothing

`Selector` gains one field:

```yaml
tap: { ref: search.field }
```

`ref` is **exclusive with every other selector field**. `{ ref: search.field, index: 2 }` is a load
error, not a refinement. The reason is the second prime directive: a merge needs a rule for what
happens when the named selector already carries `index: 0`, and every available rule (the site
wins, the definition wins, an error) is a rule an author must remember at every site. A refinement
gets its own name in the dictionary instead, where it is written once and read by everyone. This
also keeps `_non_empty` (`bajutsu/common/scenario/models/selector.py:39`) meaningful: a selector has
either exactly one `ref` or at least one condition.

An unknown name is a load error naming the name and the dictionaries searched. A dictionary entry
that is itself a `ref` is rejected — one level, no chains, so a name always resolves to a selector
by reading a single line.

### Expansion at load time, so nothing downstream changes

Resolution is a new pass in `bajutsu/common/scenario/expand.py`, running **before**
`expand_components` — so a component's steps may use `ref`, and a `${params.*}` binding cannot
fabricate a name that was not written in the source. After the pass, no `ref` remains.

Every device-free reader routes through `load_expanded_scenarios`
(`bajutsu/common/scenario/load_expanded.py:63`), so `audit`, `coverage`, `impact`, `trace --explain`,
`codegen`, and the serve Web UI's coverage view all keep reading resolved `Selector` objects. None
of them needs to learn the concept, and none of their outputs shifts. `run` keeps its own
setup-prefixing loader, which gains the same pass.

### The `serve` editor is the one place that must be taught

BE-0261's Author editor writes a picked selector into a step by re-serializing that step's block
(`bajutsu/common/scenario/edit.py`). Applied to a step whose selector is a `ref`, it would replace
the name with a literal selector — silently undoing the abstraction, exactly the kind of quiet
laxening [BE-0023](../BE-0023-self-healing-guards/BE-0023-self-healing-guards.md) exists to catch.
The editor must instead refuse the write and say why, offering to update the dictionary entry
instead. This is its own work unit and the only place a downstream consumer changes.

### Schema version

A new file-level key means an older Bajutsu reading a newer file. `ScenarioFile.schema_version`
(`bajutsu/common/scenario/models/scenario.py:314`) is the mechanism
[BE-0119](../BE-0119-scenario-schema-versioning/BE-0119-scenario-schema-versioning.md) built for
this, and the version gate runs before field validation. A file using `selectors:` declares the
bumped version, so an older reader refuses it with the version message rather than an unhelpful
"extra field" error.

### What this does not do

It does not make a selector more likely to resolve. A brittle selector referenced by name is the
same brittle selector, and `audit` grades it identically because it grades the resolved form. The
value is that it is brittle in **one place**, so improving it is one edit rather than 25. The item
should say so plainly rather than let a reader hope otherwise.

### Work breakdown (MECE)

1. **The dictionary file and its model** — a name-to-`Selector` mapping, duplicate-key rejection,
   and the `<stem>.<key>` naming.
2. **The `selectors:` file-level key**, resolved through `contained_ref`, and the schema bump.
3. **`Selector.ref`** and the exclusivity validator, with the load errors for an unknown name and a
   chained entry.
4. **The expansion pass**, ordered before component expansion, in both the device-free loader and
   `run`'s.
5. **The Author editor's refusal** and its message.
6. **Migration of the showcase suite** — the repeated identifiers moved into dictionaries, which is
   also the item's verifiable outcome.
7. **Documentation** — the grammar reference, the scenarios guide, and their Japanese mirrors.

### Prime directives preserved

- **No LLM on the run path.** Expansion is textual and deterministic, and happens before the run
  loop.
- **Determinism.** `ref` merges with nothing, so a name resolves to exactly one selector with no
  precedence rule to remember. Resolution and ambiguity are unchanged — the runner sees the same
  `Selector` it sees today.
- **App-agnostic.** The dictionary is a scenario-suite file, so per-application identifiers stay
  where the suite already keeps them rather than moving into the tool.

## Alternatives considered

- **Extend components to cover single selectors.** Rejected: a component is a sequence of steps, so
  naming a selector this way forces a step wherever the author wanted an expression, and a selector
  used inside an `expect` block cannot be reached by a step at all. It also nests: every use becomes
  a `use:` whose expansion `audit` and `coverage` must see through, for no gain over a direct
  reference.
- **Allow `ref` to merge with sibling fields as a refinement.** Genuinely convenient, and the first
  thing an author will ask for. Rejected for now: it needs a precedence rule, and whichever rule is
  chosen becomes something every author must hold in mind at every site to predict which element is
  addressed — a determinism cost paid at read time, forever, to save a dictionary entry.
- **Put the dictionary in the target's config.** Rejected: identifiers belong to the suite, not to
  the run settings, and `audit` / `coverage` / `impact` load scenarios without resolving a config —
  they would have to grow a config dependency to read a scenario. It would also make a scenario file
  unreadable on its own, which is the property that lets the suite be reviewed as text.
- **A repository-wide convention plus a lint rule ("do not repeat an id more than N times").**
  Rejected: it reports the duplication without offering anywhere to put the shared fact, so the only
  way to satisfy it is a suppression. A lint is worth adding *after* this item, when there is
  somewhere for the finding to point.

## Progress

> Keep this current as work proceeds. The checklist mirrors the MECE work breakdown in
> *Detailed design* (one box per unit of work); the log records what changed and when
> (oldest first), linking the PRs.

- [ ] The dictionary file, its model, and the naming rule.
- [ ] The `selectors:` file-level key and the schema bump.
- [ ] `Selector.ref`, the exclusivity validator, and the load errors.
- [ ] The expansion pass in both loaders.
- [ ] The Author editor's refusal.
- [ ] Showcase suite migration.
- [ ] Documentation in both languages.

Open questions to settle while building:

- Whether `triage`'s `renameId` should learn to patch the dictionary file rather than the failing
  scenario. Once the identifier lives in one place this is a small change, and it is what makes the
  self-heal complete rather than merely correct.
- Whether a dictionary may be shared across suites. Containment currently forbids it, and relaxing
  containment for this would be a larger decision than this item should make alone.
- Whether `audit` should report a named selector's stability tier against the name as well as the
  resolved form, so a report reads `search.field (stable)` rather than repeating the mapping.
- Whether `record` should write references when a name already exists for the element it picked.
  The current position is no: `record` writes literals, and a later pass factors them out.

## References

- [BE-0033 — Scenario variables + light control flow](../BE-0033-scenario-variables-control-flow/BE-0033-scenario-variables-control-flow.md)
  — the interpolation layer that carries an id string but cannot carry a selector.
- [BE-0174 — Contain scenario component and data refs within the suite root](../BE-0174-scenario-ref-path-containment/BE-0174-scenario-ref-path-containment.md)
  — the containment rule the `selectors:` reference reuses.
- [BE-0119 — Version the scenario schema for cross-version reads](../BE-0119-scenario-schema-versioning/BE-0119-scenario-schema-versioning.md)
  — the mechanism that makes a new file-level key safe for an older reader.
- [BE-0261 — Round-trip Author YAML edits through the serializer](../BE-0261-serve-author-yaml-roundtrip/BE-0261-serve-author-yaml-roundtrip.md)
  — the editor that must refuse to overwrite a reference with a literal.
- [BE-0023 — Guards against "making tests laxer"](../BE-0023-self-healing-guards/BE-0023-self-healing-guards.md)
  — why that silent replacement is the failure mode worth guarding.
- [BE-0050 — E2E coverage map](../BE-0050-e2e-coverage-map/BE-0050-e2e-coverage-map.md) and
  [BE-0321 — Test impact analysis (affected-step selection from a change)](../BE-0321-test-impact-analysis/BE-0321-test-impact-analysis.md)
  — the two identifier readers that stay unchanged because expansion precedes them.
- `bajutsu/common/scenario/models/scenario.py:294` (`Component`), `:314` (`schema_version`),
  `bajutsu/common/scenario/models/selector.py:39` (`_non_empty`),
  `bajutsu/common/scenario/expand.py:17` (`_interp_steps`),
  `bajutsu/common/scenario/load_expanded.py:21` (`contained_ref`), `:63`,
  `bajutsu/triage/heuristic.py:170` and `bajutsu/triage/cli.py:292` (the per-file rename).
