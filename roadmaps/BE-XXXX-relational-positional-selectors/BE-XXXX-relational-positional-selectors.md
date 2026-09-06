**English** · [日本語](BE-XXXX-relational-positional-selectors-ja.md)

# BE-XXXX — Relational selectors: address a control by its neighbour

<!-- BE-METADATA -->
| Field | Value |
|---|---|
| Proposal | [BE-XXXX](BE-XXXX-relational-positional-selectors.md) |
| Author | [@0x0c](https://github.com/0x0c) |
| Status | **Proposal** |
| Tracking issue | [Search](https://github.com/bajutsu-e2e/bajutsu/issues?q=is%3Aissue+label%3Aroadmap-tracking+in%3Atitle+"BE-XXXX") |
| Topic | Scenario authoring features |
| Related | [BE-0221](../BE-0221-android-scenario-portability-guarantee/BE-0221-android-scenario-portability-guarantee.md), [BE-0171](../BE-0171-element-scoped-visual-assertions/BE-0171-element-scoped-visual-assertions.md), [BE-0326](../BE-0326-scroll-to-element/BE-0326-scroll-to-element.md), [BE-0033](../BE-0033-scenario-variables-control-flow/BE-0033-scenario-variables-control-flow.md), [BE-0050](../BE-0050-e2e-coverage-map/BE-0050-e2e-coverage-map.md), [BE-0321](../BE-0321-test-impact-analysis/BE-0321-test-impact-analysis.md) |
<!-- /BE-METADATA -->

## Introduction

Five new selector fields address an element by its position relative to another one. They are
`above`, `below`, `leftOf`, `rightOf`, and `containing`. Each takes a nested `<Selector>` naming the
anchor. All five are pure geometry over the `frame` every backend already reports on `Element`
(`bajutsu/common/drivers/base.py:158`). No driver changes, no capability token, no preflight entry.
They filter the candidate set inside `find_all`. `resolve_unique`'s ambiguity rule is untouched, so
an ambiguous match still fails rather than resolving to an arbitrary element.

## Motivation

Every field a selector carries today describes the candidate itself. The one cross-element
constraint is `within`, and it expresses geometric containment alone. There is no way to write "the
field under the Email label". A screen whose controls carry no identifier is therefore reachable
three ways, each already graded weak in this repository:

- `label` / `labelMatches` — breaks when the application is translated.
- `index` — breaks when the order changes. [selectors](../../docs/selectors.md) grades it
  *last resort · flaky*.
- `tapPoint` and the coordinate gestures — break on any layout change. The bottom rung of the
  stability ladder.

An application a team owns can grow identifiers. `doctor` and
[`coverage`](../BE-0050-e2e-coverage-map/BE-0050-e2e-coverage-map.md) push exactly that way. A
third-party screen cannot. Neither can a legacy screen nobody may edit, nor a control a framework
generates. `audit` scores that situation but cannot advise on it. A selector carrying only a label
or traits draws a `moderate-selector` finding reading `is auxiliary; prefer a unique id`
(`bajutsu/analysis/audit.py:247`), and one relying on `index` draws `fragile-selector`
(`audit.py:243-246`). A unique id is the one thing such a screen cannot supply. Anchoring on a
neighbour that *does* carry an
identifier is more stable than any of the three. It survives translation, and it survives a layout
change that preserves reading order.

Once this ships, an author can point to two concrete differences from today. First, a control with
no identifier and no distinguishing label becomes addressable — an icon in a labelled row, say —
without `index` and without coordinates. Today the grammar offers those two. It also offers a
`within` scope, which helps only when the surrounding container is itself addressable. Second,
`audit` reports a `positional-selector` finding, naming the anchor a step depends on and that
anchor's own tier. Today the same step draws a finding that names the risk without naming what the
step depends on.

## Detailed design

### The five relational fields

```ebnf
Selector ::= {
  id?, idMatches?, label?, labelMatches?, traits?, value?, index?,   # unchanged
  within?:     <Selector>,   # unchanged: the candidate's frame sits inside the anchor's
  containing?: <Selector>,   # NEW: the candidate's frame encloses an element matching the anchor
  above?:      <Selector>,   # NEW ┐ at most one of above / below
  below?:      <Selector>,   # NEW │ at most one of leftOf / rightOf
  leftOf?:     <Selector>,   # NEW │ one of each axis together is legal, and AND-ed
  rightOf?:    <Selector>,   # NEW ┘
}
```

```yaml
# the input under a label that carries an id, on a screen where the input carries none
- type: { text: "a@example.com", into: { traits: [textField], below: { id: form.emailLabel } } }

# the icon to the right of a row, narrowed by trait so two icons in that row stay ambiguous
- tap: { traits: [button], rightOf: { label: "Wi-Fi" } }

# the row that encloses a known cell — the inverse of `within`
- tap: { traits: [cell], containing: { label: "Order 12345" } }
```

Three cardinality rules join [dsl-grammar](../../docs/dsl-grammar.md) §4. `above` and `below` are
mutually exclusive, and so are `leftOf` and `rightOf`. The third is new: a selector needs at least
one field that is not an anchor. `Selector._non_empty` does not cover that case. It accepts any set
field, a nested selector included. So `{below: {id: x}}` would load, and then match everything in
that column. A separate validator rejects it at load instead.

### Resolution

`find_all` (`bajutsu/common/drivers/base.py:756`) strips `within`, matches the base fields, then
filters by `contains`. The relational fields extend that chain in this order:

1. The candidate's own fields (`matches`) — unchanged.
2. The `within` scope — unchanged.
3. `containing` — a candidate survives when some element matching the anchor has its frame inside
   the candidate's. The existing `contains` (`base.py:749`) decides that.
4. Half-plane **and** cross-axis span overlap. `below` keeps candidates whose `y` starts at or past
   the anchor's bottom edge, and whose horizontal span overlaps the anchor's. The other three mirror
   it. Requiring the overlap is what makes `below` mean *in the same column, lower down* rather than
   *anywhere lower on the screen*.
5. The nearest-rank frontier. Drop a survivor when another survivor sits entirely between it and
   the anchor, along that axis. `containing` takes the symmetric rule. Drop a surviving container
   that *strictly* encloses another surviving container. `contains` is edge-inclusive, so strictly
   means it contains the other while not being contained by it. Two containers with identical frames
   therefore both survive, and stay ambiguous.
6. `resolve_unique` runs, applying its **unchanged** ambiguity rule.

Steps 4 and 5 are total pure functions of the frame set, and **neither breaks a tie**. Two controls
side by side in the first row below the anchor both survive. The selector then fails, exactly as two
same-labelled buttons fail today. The author narrows with `traits`, `labelMatches`, or `within`.

That is the point of the whole design. A relational field **filters** the candidate set and never
**picks** from it. `resolve_unique`'s guarantee therefore holds unchanged at a new site. Zero
candidates raise `ElementNotFound`. One resolves. Two or more raise `AmbiguousSelector`
([selectors](../../docs/selectors.md)).

### An anchor resolves the way `within` does, and `find_all` stays total

Every anchor is matched with `find_all` rather than `resolve_unique`. A `within` container is
matched the same way today. A candidate survives when it holds the stated relation to **some**
element the anchor matches. Two consequences follow, and both are deliberate.

**An anchor that matches nothing yields an empty candidate set** rather than an error. That keeps
`find_all` total, and eighteen call sites depend on it. `base.default_wait_for` (`base.py:965`) is
`len(find_all(driver.query(), sel)) >= 1`. Every real backend's `wait_for` delegates to it, and
`FakeDriver` and `WebContextDriver` inline the same check. Were a missing anchor to raise,
`wait: { for: { traits: [button], below: { id: x } } }` could never wait for its own anchor to
appear. That is the most natural use of a relational selector. The feature would then fight prime
directive 2 rather than serve it. `_eval_exists` with `negate: true`
(`bajutsu/common/assertions/evaluate.py:85`) and `_eval_count` with `equals: 0` (`evaluate.py:124`)
need the same totality. A `within` container that matches nothing already returns an empty list
(`base.py:783`). This is the existing contract, not a new one.

**An anchor that matches several elements widens the candidate set** rather than failing on the
spot. The extra candidates flow into `resolve_unique`, which raises `AmbiguousSelector` whenever two
or more survive. The loud failure lands one step later, at the place that already owns it. Its
message names the relational field and the anchor that widened the set, so a maintainer is not sent
looking at the target element instead.

That message is the one change to `resolve_unique`. It needs the anchor matches `find_all` already
computes and currently discards. The ambiguity rule itself does not move.

The widening is loud only when it leaves two or more candidates. Two anchors above one shared
candidate leave a single survivor. `resolve_unique` also collapses content-identical candidates
before counting (`_collapse_identical_duplicates`, `base.py:862-875`). An ambiguous anchor can
therefore still resolve, and do it silently. Whether that residual case deserves its own diagnosis
is an open question below, and it is about more than message quality.

### `audit` grades the candidate, and reports the anchor separately

`_tier` (`bajutsu/analysis/audit.py:54-60`) grades three ways today. `id` and `idMatches` are
`stable`. `label`, `labelMatches`, `traits`, `value`, and `within` are `moderate`. `index` is
`fragile`. A relational field gets **no tier of its own**, because its stability is inherited from
its anchor. Anchoring on a stable identifier and anchoring on a translated label are not the same
risk. The candidate keeps being graded by its own fields. The relational field is recorded
separately, as a `Finding(kind="positional-selector")` naming the anchor and the anchor's tier.
`audit` then explains what a step depends on instead of merely scoring it.

`_with_nested` (`audit.py:63`) descends into `within` alone today. It must descend into all six
nested anchors. Without that,
[`coverage`](../BE-0050-e2e-coverage-map/BE-0050-e2e-coverage-map.md) under-counts. And
[`impact`](../BE-0321-test-impact-analysis/BE-0321-test-impact-analysis.md) misses a step whose
sole identifier reference is its anchor.

### Backends, and two stated limits

Every backend works, with no capability token and no preflight row. `frame` is a required field of
`Element`. All four of `xcuitest`, `adb`, `playwright`, and `fake` populate it.

**Inside a `web` block** the `WebContextDriver`'s frames live in the WebView's own coordinate space.
Relational selectors stay self-consistent within the block. They must not relate a native element to
a DOM element.

**An element absent from the tree stays unreachable.** Relational selectors express geometry between
elements the tree reports. They do not summon one it omits. The `tapPoint` in
`demos/showcase/ios/scenarios-noax/generated.yaml` is the worked example. Its own `from:` records
why: the tab is *"not in the element list, so I tap its visible center"*. That step does not migrate,
and this item claims no improvement there.

### Codegen

The three emitters refuse the new fields loudly. They join the unsupported-field lists the emitters
already carry, `playwright._UNSUPPORTED_FIELDS` among them. Emitting a weaker selector silently
would hand a team a native test that checks less than the scenario did.

### Work breakdown (MECE)

1. **Grammar** (`bajutsu/common/scenario/models/selector.py`). The five fields, the two
   axis-exclusion validators, and the third validator requiring one non-anchor field, plus the
   [dsl-grammar](../../docs/dsl-grammar.md) §2 and §4 productions with the Japanese mirror. The
   self-reference needs no new `model_rebuild()`.
2. **Geometry helpers** (`bajutsu/common/drivers/base.py`). `beyond` and `spans_overlap` beside
   `contains`, keeping the geometry in one module, with a pure unit suite.
3. **Resolution** (`base.find_all`). The filter chain and the frontier, with `resolve_unique`'s
   ambiguity rule untouched. `find_all` stays total, proven by tests over the call sites that depend
   on it:
   `base.default_wait_for`, `_eval_exists` with `negate: true`, and `_eval_count` with `equals: 0`.
   The driver conformance suite
   ([BE-0114](../BE-0114-driver-conformance-suite/BE-0114-driver-conformance-suite.md)) is extended
   so every backend proves the same answers.
4. **Anchor-attributed failures**. `resolve_unique`'s `AmbiguousSelector` message names the
   relational field and the anchor that widened the candidate set. That needs the anchor matches
   carried out of `find_all` rather than discarded, and the message written in the register the
   existing `base.py` messages already use.
5. **Static-analysis walk** (`bajutsu/analysis/audit.py`). `_with_nested` descends into all six
   anchors, and `_describe` excludes them from a selector's own text as it already excludes `within`.
   Regressions cover an identifier referenced from an anchor alone, in `coverage` and in `impact`.
6. **`audit` reporting**. The `positional-selector` finding, and its row in
   [cli](../../docs/cli.md).
7. **Codegen refusal**. The three emitters name the unsupported field and point at `bajutsu run`.
8. **Documentation**. The [selectors](../../docs/selectors.md) resolution table, a worked example in
   [scenarios](../../docs/scenarios.md), the two limits above written out, and the Japanese mirrors.

### Prime directives preserved

- **No LLM on the run path.** Resolution is arithmetic over frames the driver already reports. The
  verdict still comes from machine-checkable assertions.
- **Determinism.** A relational field narrows the candidate set and never selects from it, so
  `resolve_unique`'s ambiguity rule is unchanged. The frontier removes candidates that are provably
  farther and then stops; it never breaks a tie.
- **App-agnostic.** The fields are identical across every target. Nothing here is specific to one
  application or one backend.
- **Codegen.** The new fields join the existing loud refusals. They never degrade into a weaker
  emitted selector.

## Alternatives considered

- **Take the candidate nearest the anchor after the half-plane filter, and resolve to it.**
  Rejected: it reintroduces "resolve to whatever the filter ordered first" at a new site.
  [selectors](../../docs/selectors.md)'s `resolve_unique` contract and prime directive 2 both forbid
  that. The nearest-**rank frontier** buys the usability without the pick. It removes candidates
  that are provably farther and stops there, leaving a genuine tie to fail.
- **Do nothing, and keep pushing teams to add identifiers.** Rejected, with the limit of that
  answer stated rather than hidden. It holds for an application a team owns. It fails for a
  third-party or legacy screen. The fallback there is `tapPoint`, which survives neither translation
  nor layout change, and about which `audit` can say nothing actionable.
- **Add a hierarchical parent/child query to the `Driver` Protocol, so `childOf` is structural
  rather than geometric.** Rejected: the normalized `Element` tree is flat across all four backends
  by construction. Adding parent links is a `Driver` API change every backend must satisfy, for one
  selector family. `within`'s geometric containment already carries `childOf`'s meaning, and
  `containing` carries its inverse. A flat tree cannot distinguish a direct child from a deeper
  descendant, so one field covers both. That is stated here rather than left for a reader to
  discover.

## Progress

> Keep this current as work proceeds. The checklist mirrors the MECE work breakdown in
> *Detailed design* (one box per unit of work); the log records what changed and when
> (oldest first), linking the PRs.

- [ ] Grammar — the five `Selector` fields, the three validators, and the DSL grammar.
- [ ] Geometry helpers — `beyond` and `spans_overlap` beside `contains`, with a pure unit suite.
- [ ] Resolution — the `find_all` filter chain and the frontier, its totality proven over
      `default_wait_for` / `exists` / `count`, and the conformance suite extended.
- [ ] `AmbiguousSelector` naming the relational field and the anchor that widened the set.
- [ ] Static-analysis walk — `_with_nested` over all six anchors, `_describe` excluding them, with
      `coverage` / `impact` regressions.
- [ ] `audit` reporting — the `positional-selector` finding and its CLI reference row.
- [ ] Codegen refusal in the three emitters.
- [ ] Documentation — the selectors resolution table, a scenarios example, the two limits, and the
      Japanese mirrors.

Open questions to settle while building:

- Whether the frontier needs an opt-out for an author who wants every candidate on that side. The
  default is the frontier, and an opt-out would need a determinism argument of its own.
- Whether an anchor matching several elements deserves a distinct diagnosis. It currently widens the
  candidate set and surfaces as an ordinary `AmbiguousSelector`, which conflates two causes: a target
  that is genuinely ambiguous, and an anchor that was. Worse, a widening that still leaves one
  survivor resolves with no diagnosis at all.
- How `index` and the frontier compose. `index` counts the `other`-filtered set today, and would
  count the frontier set after this change. The ordering needs stating, or the two features will
  surprise each other.
- Frames on a scrolled container. A candidate below the anchor but off-screen may report a frame
  outside the viewport on one backend, and be clipped on another. The conformance suite pins one
  answer.
- Whether `record` should ever author a relational selector. The current position is no. `record`
  stays identifier-first, and a relational field is a hand-authoring escape.

## References

- [selectors](../../docs/selectors.md) — `resolve_unique`, the stability ladder, and the `within`
  containment this extends.
- [dsl-grammar](../../docs/dsl-grammar.md) — the `Selector` production and the §4 cardinality rules.
- [BE-0221 — Guarantee shared showcase scenarios run unchanged on Android](../BE-0221-android-scenario-portability-guarantee/BE-0221-android-scenario-portability-guarantee.md)
  — the id candidate list, the other selector-grammar widening that left resolution unchanged.
- [BE-0171 — Element-scoped visual assertions and selector-based masking](../BE-0171-element-scoped-visual-assertions/BE-0171-element-scoped-visual-assertions.md)
  — the other consumer of `Element.frame`; it scopes a comparison where this scopes a selection.
- [BE-0326 — The `scroll` action: scroll until an element appears](../BE-0326-scroll-to-element/BE-0326-scroll-to-element.md) — brings
  an element on screen, which an anchored selector composes with, since the anchor must be visible for
  the geometry to hold.
- [BE-0050 — E2E coverage map](../BE-0050-e2e-coverage-map/BE-0050-e2e-coverage-map.md) and
  [BE-0321 — Test impact analysis (affected-step selection from a change)](../BE-0321-test-impact-analysis/BE-0321-test-impact-analysis.md) —
  the static readers that must see an anchor's identifier.
- `bajutsu/common/drivers/base.py` (`Element`, `contains`, `find_all`, `resolve_unique`),
  `bajutsu/analysis/audit.py` (`_tier`, `_with_nested`, `_selector_finding`).
