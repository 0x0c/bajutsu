# Language-neutral selector-resolution fixtures (BE-0408)

Two fixture sets a future Swift ([BE-0409](../../../roadmaps/BE-0409-step-latency-ios-device-executor/BE-0409-step-latency-ios-device-executor.md))
and Kotlin ([BE-0410](../../../roadmaps/BE-0410-step-latency-android-device-executor/BE-0410-step-latency-android-device-executor.md))
selector resolver must agree with, ported from the Python reference implementation these fixtures
are also replayed against (`tests/test_selector_fixtures.py`) — so a drift between the fixtures and
the reference fails the fast gate the moment either one changes, rather than surfacing only once a
device-side port exists to disagree with it. See the porting-contract narrative in
[`docs/selectors.md`](../../../docs/selectors.md#porting-contract-for-a-device-side-resolver) (and
its [Japanese mirror](../../../docs/ja/selectors.md)) for the prose version of every rule these
cases pin.

## `selector_resolution.json`

`find_all` / `resolve_unique` (`bajutsu/common/drivers/base/_functions.py`) semantics: what
matches, in what order, and which of the three outcomes (`resolved`, `notFound`, `ambiguous`) a
`resolveUnique`-style single-element resolution reaches. Every case is one screen (`elements`) plus
one `selector`, checked against `findAll.identifiers` (the ordered id list `find_all` should
return) and/or `resolveUnique` (the outcome a caller like an action handler's single-target
resolution should reach — `identifier` and, where an identifier alone cannot disambiguate a
`within` result, an exact `frame` pin).

Ported from `tests/test_resolve.py`'s 28 semantic cases (its four purely Python-internal
mechanism tests — the `_compile` cache, the `_id_index` cache, `id_candidates`'s scalar/list
normalization — are implementation caching details, not selector semantics, so they carry nothing
for a device-side port and are not fixtured here). Covers: exact `id` / OR-candidate-list `id`
matching (BE-0221), glob `idMatches` (`fnmatch.fnmatchcase`, fully anchored) vs. regex
`labelMatches` (`re.search`, unanchored) as two distinct matching engines, `traits` as a subset
test, `within`'s geometric (edge-inclusive, non-hierarchical, nestable) containment, positive and
negative `index` (including out-of-range at either end, and against zero candidates), identical
duplicate collapsing (exact frame, trait-set key), and the `other`-trait ambiguity-drop heuristic
(including how it interacts with an explicit `traits: ["other"]` selector and with `index`).
`nativeZ` is deliberately absent from this format's own `Element` shape — it never enters
`_collapse_identical_duplicates`'s key on the host either, and its exclusion is stated as prose in
`docs/selectors.md`'s porting-contract section rather than pinned by a fixture case here, since a
format with no `nativeZ` field cannot itself express "this field is excluded from the key."

## `android_derived_label.json`

The Android-only label-derivation rule for a clickable node carrying neither `text` nor
`content-desc` (`bajutsu/common/drivers/adb/_functions.py`'s `_derived_label`, called from
`_to_element`). Unlike the selector-resolution cases above, this operates one layer earlier — on
raw `dumpWindowHierarchy` XML, before an `Element` exists at all — so each case is a literal
`<hierarchy>` XML fragment (the same shape `parse_hierarchy` consumes, matching the precedent in
`tests/test_adb.py`) plus the `frame` of the node under test and its `expectedLabel`. Covers: `text`
and `content-desc` both winning outright over derivation, a non-clickable container never deriving
(derivation is scoped to `clickable="true"` nodes only), the depth-first pre-order join of
non-clickable descendants' text, a nested clickable descendant's subtree being skipped entirely
(it is its own control, with its own derived label), and the empty-result-degrades-to-`None` case.
A device-side Android executor's own on-device normalization needs to reach the same label a
selector authored against the host's `/source` read would expect, or a label-based selector could
resolve on one side and fail on the other — exactly the determinism regression
[BE-0408](../../../roadmaps/BE-0408-step-latency-device-executor-protocol/BE-0408-step-latency-device-executor-protocol.md)'s
Motivation warns against.

## Schema

| Field | Meaning |
|---|---|
| `schema` | the fixture format's version; a load refuses an unknown one rather than reading old cases under new rules |
| `cases[].name` | a stable identifier for the case, traceable back to the Python test it was ported from |
| `cases[].note` | why this case exists, quoted from the Python test's own comment where one existed |

`selector_resolution.json` additionally: `elements` (one `query()`-shaped snapshot: `identifier`,
`label`, `traits`, `value`, `frame` — every field spelled out explicitly, `null`/`[]` for absence,
no implicit defaulting, since the whole point is a contract two independent ports cannot silently
diverge from), `selector` (a `Selector` object, nesting `within` where needed), `findAll` (present
when the case checks `find_all`'s result), `resolveUnique` (present when the case checks a
single-element resolution: `outcome` one of `resolved` / `notFound` / `ambiguous`; `identifier` and
optionally `frame` when `resolved`; `reason` — `noMatch` or `outOfRange`, a normalized English
classification rather than the Python implementation's literal Japanese message text — when
`notFound`).

`android_derived_label.json` additionally: `xml` (a `<hierarchy>...</hierarchy>` fragment), a
`targetFrame` naming which parsed node the case is about, and `expectedLabel`.

## Not re-captured from a device

Unlike `tests/fixtures/be0308/`, these fixtures are not captured from a real device — they encode
a deterministic, pure-function contract (`find_all` / `resolve_unique` / `_derived_label` take no
device state as input), so they are authored directly and kept in step with
`bajutsu/common/drivers/base/_functions.py` and `bajutsu/common/drivers/adb/_functions.py` by hand.
`tests/test_selector_fixtures.py` fails the fast gate the moment either source file's behavior
drifts from a case here.
