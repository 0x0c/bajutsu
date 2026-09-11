**English** · [日本語](BE-0420-scenario-slug-length-cap-ja.md)

# BE-0420 — Cap scenario evidence-directory slug length

<!-- BE-METADATA -->
| Field | Value |
|---|---|
| Proposal | [BE-0420](BE-0420-scenario-slug-length-cap.md) |
| Author | [@0x0c](https://github.com/0x0c) |
| Status | **Implemented** |
| Tracking issue | [Search](https://github.com/bajutsu-e2e/bajutsu/issues?q=is%3Aissue+label%3Aroadmap-tracking+in%3Atitle+"BE-0420") |
| Topic | Codebase quality & technical debt |
| Related | [BE-0417](../BE-0417-scenario-result-folder-naming/BE-0417-scenario-result-folder-naming.md), [BE-0031](../BE-0031-data-driven-scenarios/BE-0031-data-driven-scenarios.md) |
<!-- /BE-METADATA -->

## Introduction

Bajutsu writes each scenario's evidence under `runs/<runId>/<sid>/`. `_evidence_sid()`
([`bajutsu/common/runner/pipeline.py:82`](../../bajutsu/common/runner/pipeline.py)) builds `sid`
from a two-digit run-order index plus one of two slugs. A scenario loaded from a file gets
`sanitize_source_stem(s.source_stem)`, the file's own stem with unsafe characters replaced
([BE-0417](../BE-0417-scenario-result-folder-naming/BE-0417-scenario-result-folder-naming.md),
**Implemented**). A scenario with no known source file falls back to `scenario_slug(s.name)`.
Neither function caps its output length. A long source-file stem, or a long scenario `name`,
produces an arbitrarily long `sid`, and the evidence directory fails to write.

This item adds a fixed length cap to both functions. `sanitize_source_stem()` preserves Unicode
letters, so its cap counts UTF-8 bytes. `scenario_slug()` reduces its input to ASCII first, so a
character count and a byte count are the same for it. Either way, the function now truncates an
oversized slug instead of growing it without bound. `sid` then stays under a safe length,
regardless of what produced it.

### Not doing

- **The top-level run directory (`runs/<runId>/`, a UTC timestamp) is unchanged.** This item
  touches the two slugs nested under it, alone.
- **`Scenario.name` and `Scenario.source_stem` stay untruncated.** `name` also feeds
  `manifest.json`'s `scenario` field, `report.html`, and `declared_name()`'s row-suffix matching
  for serve's run pickers
  ([`bajutsu/common/scenario/expand.py:117`](../../bajutsu/common/scenario/expand.py)).
  `source_stem` has one reader today, `_evidence_sid()` itself. This item still caps only the slug
  it derives, not the field. A future second reader of `source_stem` then never receives a
  silently shortened value.
- **No new duplicate-suffix counter.** Every `sid` `_evidence_sid()` builds carries the
  `{i:02d}-` index prefix, which keeps it unique within a run, truncated slug or not. Two
  fallbacks build a bare slug with no such prefix, and can collide after truncation where they do
  not today:
  - `scenario_slug(scenario.name)`, when a direct `run_scenario` caller passes no `scenario_id`
    ([`bajutsu/common/orchestrator/loop/_functions.py:645`](../../bajutsu/common/orchestrator/loop/_functions.py))
  - `scenario_slug(r.scenario)`, for a `sid`-less result in the report matrix
    ([`bajutsu/common/report/manifest.py:127`](../../bajutsu/common/report/manifest.py))

  Neither sits on the `run` CLI's own path: `pipeline.py:796` always passes `scenario_id=sid`, and
  `pipeline.py:1253` builds `sid` through `_evidence_sid()` itself. This item leaves both call
  sites unchanged — capping `scenario_slug()` still shortens what they produce.
- **`record`'s own file-naming is unchanged.** An authored scenario with no explicit save name
  falls back to the recording's natural-language goal
  (`scenario_out_name()`, [`bajutsu/serve/helpers.py:454`](../../bajutsu/serve/helpers.py)). That
  function has no length cap either. This item caps the evidence-directory slug a long file name
  can produce, not the file name itself. A long `*.yaml` file name is legible on disk and blocks
  nothing on its own. The evidence directory it produces competes with a real filesystem limit on
  every run of that file.

## Motivation

[BE-0417](../BE-0417-scenario-result-folder-naming/BE-0417-scenario-result-folder-naming.md)
already closes the failure this item was first reported against. Before it landed, every
CSV-expanded row of a data-driven scenario
([BE-0031](../BE-0031-data-driven-scenarios/BE-0031-data-driven-scenarios.md)) carried its own
`key=value` parameter text in `name`. A long or many-columned row could then turn
`scenario_slug(s.name)`'s output into an oversized `sid`. Both file loaders now stamp
`source_stem` on every row after expansion:

- [`bajutsu/run/cli.py:201`](../../bajutsu/run/cli.py)
- [`bajutsu/common/scenario/load_expanded.py:91`](../../bajutsu/common/scenario/load_expanded.py)

Every row of one file now shares that file's own short stem. `_evidence_sid()` no longer reaches
`scenario_slug()` for a data-driven scenario at all.

The same class of failure still reaches two paths neither slug function caps. The first is a long
source file. `record`'s own auto-naming falls back to the recording's natural-language goal when
an operator gives no `--out` and no explicit name (see *Not doing*). A verbose goal — "log in with
a saved card, confirm the checkout total matches the cart, and check the confirmation email
arrives" — produces a `*.yaml` file exactly that long. Every later run of that file then tries to
create an evidence directory of the same length.

The second path is a scenario built directly, outside the file loaders. This covers the two
bare-fallback call sites in *Not doing*. It also covers any caller of `run_scenario()` that
constructs a `Scenario` itself, rather than loading one from a file — for example
[`demos/showcase/record/generate_from_nl.py`](../../demos/showcase/record/generate_from_nl.py).
Every one of these still falls back to `scenario_slug(s.name)`, uncapped.

Capping both functions closes both paths at their own single definition — the same choke point
`_evidence_sid()` and the two bare fallbacks already share. Once this item lands, a scenario with
a long or verbose source file — or, lacking one, a long or verbose `name` — still runs to
completion and writes its evidence directory.

## Detailed design

1. **A shared byte-safe truncation helper.** Add `_MAX_SLUG_BYTES = 60` and a private
   `_cap_bytes(slug: str) -> str` beside `scenario_slug()` and `sanitize_source_stem()` in
   [`bajutsu/common/orchestrator/types/_functions.py`](../../bajutsu/common/orchestrator/types/_functions.py).
   `_cap_bytes` encodes `slug` to UTF-8. When that exceeds `_MAX_SLUG_BYTES`, it slices the encoded
   bytes to that budget and decodes with `errors="ignore"`. That drops a partial trailing character
   instead of raising. One helper, one budget, serves both functions: `scenario_slug()`'s output is
   pure ASCII, so a byte slice there is exactly a character slice, and today's
   `.strip("-").lower()` ordering is unaffected.
2. **`scenario_slug()` calls it last.** The existing regex first collapses each run of
   non-alphanumeric characters to `-`, strips the result, and lowercases it. Pass that string
   through `_cap_bytes` next, then `.rstrip("-")` to drop a hyphen the cut may leave dangling. Fall
   back to `"scenario"` when that leaves nothing — the function already returns that same fallback
   for an all-symbol name.
3. **`sanitize_source_stem()` calls it last.** The existing `re.sub(r"[^\w.-]", "_", stem)` first
   replaces every unsafe character; pass the result through `_cap_bytes` next. No further fallback
   is needed. The smallest encoded character is one byte, so a 60-byte budget can only ever produce
   an empty string when the input itself was already empty. `re.sub` cannot produce that from a
   non-empty `stem`: a source file's stem is never empty, since `Path.stem` on a `*.yaml` file
   always yields at least one character.
4. **No call site changes.** `_evidence_sid()`'s two branches, and the two bare-fallback call
   sites in *Not doing*, all call `scenario_slug()` or `sanitize_source_stem()` directly. The cap
   reaches every one of them without touching a single call site.
5. **Docs.** [`docs/reporting.md`](../../docs/reporting.md) /
   [`docs/ja/reporting.md`](../../docs/ja/reporting.md) gain a short paragraph beside the existing
   `runId` / `stepId` line, naming `sid`'s two possible sources and the shared cap.
6. **Tests.**
   - A unit test for `scenario_slug()`: an overlong name comes back capped, with no trailing
     hyphen.
   - A unit test for `sanitize_source_stem()`: an overlong ASCII stem comes back capped at 60
     bytes.
   - A unit test for `sanitize_source_stem()`: an overlong stem built from multi-byte characters
     (for example repeated `決済フロー`) comes back at or under 60 bytes, as valid UTF-8, with no
     half-written character.
   - A unit test reproducing the `record`-with-no-`--out` case: a long natural-language goal, run
     through `scenario_out_name()` then `sanitize_source_stem()`, produces a `sid` within the cap.
   - A test that colliding truncated slugs still land in distinct directories, via the existing
     `{i:02d}-` index prefix.

## Alternatives considered

| Alternative | Why we did not take it |
|---|---|
| Refuse a scenario whose slug would exceed the cap, mirroring [BE-0404](../BE-0404-collapse-project-layer/BE-0404-collapse-project-layer.md)'s "refuse, don't truncate" rule for run-history labels (`MAX_LABEL_LENGTH`, `bajutsu/common/report/manifest.py:13`) | A run-history label is text an operator typed and expects preserved exactly. Refusing it hands control back to the operator. `sid`'s slug is a derived filesystem id nobody authors directly — an operator recording a long natural-language goal is not choosing a file name, they are describing a flow. Refusing to run over that description blocks the whole scenario, where a legible, truncated slug does not. |
| Hash the slug to a fixed-length digest instead of truncating it | A digest carries none of the original name or file stem, defeating the reason both functions derive the directory name from the scenario in the first place: letting an operator recognize a result by eye. Truncation keeps the recognizable lead. |
| Truncate `Scenario.name` or `Scenario.source_stem` themselves, before the slug functions run | `name` also feeds `manifest.json`'s `scenario` field, `report.html`, and `declared_name()`'s row-suffix matching. `source_stem` has one reader today, but truncating the field itself would silently hand a shortened value to any future second reader. `sid` is the only consumer that is purely a filesystem identifier, so it is the only thing this item caps. |
| Make the cap configurable per target | The cap protects a filesystem write, not app behavior. The app-agnostic boundary (prime directive 3) puts per-app differences in config, not a filesystem constant that holds the same regardless of the target under test. |
| Keep the row-distinguishing suffix instead of the scenario name's own lead — truncate from the front, or elide the middle (a head fragment plus a tail fragment) | This weighs a suffix that no longer reaches `scenario_slug()` for the common data-driven case (*Motivation*): every such row now shares one source-file stem, told apart only by the `{i:02d}-` index already, cap or no cap. For the two paths this item does address — a long file name, a long in-memory `name` — the lead is what an operator recognizes on sight; a head-and-tail elision would preserve slightly more of either at the cost of a second slice, a wider test matrix, and a slug that no longer reads as one continuous name at a glance. |
| Cap `scenario_out_name()` (`record`'s own file-naming) instead of, or in addition to, the two slug functions | Fixes only the case a `record` session with no `--out` produces; a hand-authored file with an equally long name reaches the same failure through `sanitize_source_stem()` untouched. Capping at the two slug functions protects every path that reaches `sid` — recorded, hand-authored, or built in memory — from one definition, regardless of how the source file (if any) got its name. |

## Progress

> Keep this current as work proceeds. The checklist mirrors the MECE work breakdown in
> *Detailed design* (one box per unit of work); the log records what changed and when
> (oldest first), linking the PRs.

- [x] Unit 1 — `_MAX_SLUG_BYTES = 60` and a private `_cap_bytes()` helper. Both sit beside the two
  slug functions in `bajutsu/common/orchestrator/types/_functions.py`. The helper encodes to UTF-8.
  It slices the encoding to the budget when the encoding runs past it. Decoding with
  `errors="ignore"` then drops a character the cut would split, rather than raising.
- [x] Unit 2 — `scenario_slug()` passes its lowercased result through `_cap_bytes()` last. A
  `.rstrip("-")` follows, dropping a separator the cut can leave dangling. The existing
  `"scenario"` fallback still covers an all-symbol name.
- [x] Unit 3 — `sanitize_source_stem()` passes its `re.sub()` result through `_cap_bytes()` last.
  The change needs no further fallback. The smallest encoded character is one byte. An empty stem
  is then the sole input that could yield an empty result.
- [x] Unit 4 — No call site changed, as designed. Both `_evidence_sid()` branches call one of the
  two capped functions directly. The two bare fallbacks do the same, at `loop/_functions.py:645`
  and `report/manifest.py:127`. The cap reaches every one of them from its single definition.
- [x] Unit 5 — `docs/reporting.md` and `docs/ja/reporting.md` each gained a paragraph. It sits
  beside the existing `runId` / `sid` / `stepId` line. The paragraph names the shared cap and why
  the cap counts bytes rather than characters. It also records that `Scenario.name` itself stays
  untruncated.
- [x] Unit 6 — Six unit tests in `tests/runner/test_pipeline.py`, beside the existing BE-0417 slug
  tests. The count is one more than the design's five. The dangling-separator case became its own
  test, not a second assertion on the overlong-name one. A regression then names the broken
  property. The six cases:
  - an ASCII slug capped with no trailing hyphen;
  - a cut landing on a separator;
  - a capped ASCII stem;
  - a multi-byte stem whose budget lands inside a character;
  - the `record`-with-no-`--out` path through `scenario_out_name()`;
  - colliding truncated slugs still drawing distinct `sid`s from the `{i:02d}-` prefix.

## References

- [BE-0417 — Name a scenario's evidence directory after its source file](../BE-0417-scenario-result-folder-naming/BE-0417-scenario-result-folder-naming.md) (Implemented, [#1977](https://github.com/bajutsu-e2e/bajutsu/pull/1977))
- [BE-0031 — Data-driven scenarios](../BE-0031-data-driven-scenarios/BE-0031-data-driven-scenarios.md)
- [BE-0404 — Collapse the project layer](../BE-0404-collapse-project-layer/BE-0404-collapse-project-layer.md)
- [`bajutsu/common/orchestrator/types/_functions.py`](../../bajutsu/common/orchestrator/types/_functions.py)
- [`bajutsu/common/runner/pipeline.py`](../../bajutsu/common/runner/pipeline.py)
- [`bajutsu/common/report/manifest.py`](../../bajutsu/common/report/manifest.py)
- [`bajutsu/common/orchestrator/loop/_functions.py`](../../bajutsu/common/orchestrator/loop/_functions.py)
- [`bajutsu/serve/helpers.py`](../../bajutsu/serve/helpers.py)
- [`docs/reporting.md`](../../docs/reporting.md)
