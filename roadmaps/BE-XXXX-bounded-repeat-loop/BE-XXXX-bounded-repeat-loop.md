**English** · [日本語](BE-XXXX-bounded-repeat-loop-ja.md)

# BE-XXXX — A counted and a bounded conditional loop

<!-- BE-METADATA -->
| Field | Value |
|---|---|
| Proposal | [BE-XXXX](BE-XXXX-bounded-repeat-loop.md) |
| Author | [@0x0c](https://github.com/0x0c) |
| Status | **Proposal** |
| Tracking issue | [Search](https://github.com/bajutsu-e2e/bajutsu/issues?q=is%3Aissue+label%3Aroadmap-tracking+in%3Atitle+"BE-XXXX") |
| Topic | Scenario authoring features |
| Related | [BE-0033](../BE-0033-scenario-variables-control-flow/BE-0033-scenario-variables-control-flow.md), [BE-0326](../BE-0326-scroll-to-element/BE-0326-scroll-to-element.md), [BE-0400](../BE-0400-scroll-step-amount/BE-0400-scroll-step-amount.md), [BE-0082](../BE-0082-capability-preflight-check/BE-0082-capability-preflight-check.md), [BE-0392](../BE-0392-scenario-before-after-hooks/BE-0392-scenario-before-after-hooks.md), [BE-0297](../BE-0297-codegen-xcuitest-dsl-coverage/BE-0297-codegen-xcuitest-dsl-coverage.md) |
<!-- /BE-METADATA -->

## Introduction

A `repeat` step runs a body of steps more than once, in one of two bounded forms. `repeat: { times:
N, steps: [...] }` runs the body exactly N times. `repeat: { while: <Assertion>, maxIterations: M,
steps: [...] }` re-evaluates a machine-checkable assertion before each iteration and runs the body
while it holds, failing the step when it reaches the bound with the condition still true.
`maxIterations` is required and both bounds are capped by the model, so no scenario the loader
accepts can express a loop that fails to terminate.

## Motivation

"Tap Add five times" is five copied steps today. "Delete until the inbox is empty" has no form at
all. The first is a maintenance cost, since five near-identical steps read as five intentions rather
than one. The second is a capability gap, and it pushes an author toward a fixed count that is wrong
on a different data set.

[BE-0033](../BE-0033-scenario-variables-control-flow/BE-0033-scenario-variables-control-flow.md)
named this gap and left it open. Its Motivation lists "a flow that … repeats a step a bounded number
of times" among the shape variations authors need, and its Alternatives rejected "a general
scripting/expression language" because "arbitrary expressions and **unbounded** loops would let a
scenario diverge or make pass/fail depend on logic the runner cannot bound". That reasoning rules out
an unbounded loop. It does not rule out a bounded one, and BE-0033 shipped `forEach` on exactly that
argument: the loop "is bounded by the statically resolved match set and always terminates".

`scroll` already carries the shape a bounded conditional loop needs. An author states a step bound
(`maxScrolls`, default 15, `gt=0`), the runner re-checks a condition each step, and reaching the
bound is a **failure** rather than a quiet exit
([BE-0326](../BE-0326-scroll-to-element/BE-0326-scroll-to-element.md), refined by
[BE-0400](../BE-0400-scroll-step-amount/BE-0400-scroll-step-amount.md)). Generalizing that shape from
one action to a body of steps is the whole of this proposal.

Once this ships, a reader can point to two differences. First, a repetition that appears today as N
near-identical consecutive steps in a scenario file appears as one step, while the run's
`manifest.json` still records N actuations. Second, a scenario expressing "until the list is empty"
exists in the repository, where today no scenario can express it at all.

## Detailed design

### The `repeat` action

```ebnf
Action ::= … | { repeat: <Repeat> }        # no capture / extract, as with `if` and `forEach`

Repeat ::= { times: integer, as?: string, steps: list(<Step>) }                    ┐ XOR
         | { while: <Assertion>, maxIterations: integer, as?: string,
             steps: list(<Step>) }                                                 ┘
    # times:         1 ≤ times ≤ 100
    # maxIterations: required, 1 ≤ maxIterations ≤ 100
    # as:            binds the 1-origin iteration number to vars.<as>, as forEach binds its element
```

```yaml
# a fixed count the author knows
- repeat:
    times: 5
    steps:
      - tap: { id: cart.add }

# a condition the screen decides, under a bound the author wrote
- repeat:
    while: { exists: { id: inbox.row } }
    maxIterations: 20
    steps:
      - tap: { id: inbox.row, index: 0 }
      - tap: { id: inbox.confirmDelete }
```

### Termination is structural, not advisory

Three decisions carry that, and each is deliberate.

**`maxIterations` is required.** `scroll.maxScrolls` may default to 15 because it guards a physical
process with a natural end condition — the target is on screen or it is not. A `while` body is
arbitrary author-written work, so the bound *is* the author's contract, and the grammar refuses a
loop that does not state it. The grammar therefore cannot express an unbounded loop. It does not
merely discourage one.

**Both bounds are capped at 100 by the model**, the way `Pinch.scale > 0` is enforced today. Worst
case body executions are bounded by the file itself, so BE-0033's "always terminates" property is
preserved by construction rather than by convention.

**Reaching `maxIterations` with the condition still true fails the step**, with a reason naming the
iteration count and the condition. A silent exit would let a scenario go green having done less than
the author asked, which is the failure mode `scroll`'s fail-at-a-bound already refuses.

### Runtime

`_run_repeat` joins `_run_if` and `_run_for_each` in
`bajutsu/common/orchestrator/loop.py`, returning the same `tuple[bool, str]`, and the step dispatch
gains a `"repeat"` arm beside `"if_"` and `"for_each"` (`loop.py:1281-1284`). The condition
evaluation `_run_if` performs today — interpolate the assertion against `bindings`, `driver.query()`,
evaluate — is factored into one `_eval_condition` helper shared by `_run_if`, `_run_repeat`, and the
interrupt guard, so one predicate path exists rather than two that can diverge.

A condition is an `Assertion`, so `while: { count: { sel: …, atLeast: 1 } }` and `while: { request:
… }` both work, and no model is consulted anywhere — the property `if` already has. Nesting reuses
`_StepCounter`, so the manifest shows each iteration's evidence under its own path and nothing about
evidence is special-cased.

### The five walks that must learn the new arm

Each already carries an `if_` / `for_each` pair. Missing one is a defect, not an omission:

- `bajutsu/common/capability/capability_preflight.py` `_walk_steps` (`:83-87`). Without it an
  unsupported step inside a loop body escapes the gate and fails late on a device — the exact thing
  [BE-0082](../BE-0082-capability-preflight-check/BE-0082-capability-preflight-check.md) exists to
  prevent.
- `bajutsu/analysis/audit.py`'s selector and finding walks.
- `bajutsu/analysis/coverage.py`'s request walk.
- `bajutsu/analysis/trace.py`'s control-flow predicate.
- `bajutsu/codegen/common.py` `_reject_runtime_only` (`:263`).

### `audit` and `impact` across a loop

`audit` grades a body selector **once**, not `times` times. A selector's stability is a property of
the selector, not of how often it runs, and counting it N times would let a loop inflate a scenario's
stability fraction. A new `loose-loop` finding covers a `while` whose condition is one of the loose
forms `audit` already names, and a `while` sitting at the 100 ceiling.

`impact` attributes body steps to the enclosing `repeat` step's own index, exactly as `forEach` body
steps are attributed today, so `StepRef` needs no change. `coverage` folds body-referenced ids and
endpoints in unchanged.

### Codegen takes `times` and refuses `while`

`if`, `forEach`, and `extract` are refused today because a static test has no runtime to reproduce
them ([BE-0297](../BE-0297-codegen-xcuitest-dsl-coverage/BE-0297-codegen-xcuitest-dsl-coverage.md)).
`repeat: { times: N }` differs: the bound is a compile-time constant, so it maps faithfully onto a
counted loop in Swift, TypeScript, and Kotlin alike. **`times` is emitted; `while` joins
`_reject_runtime_only`.** This is the first control-flow form codegen can translate, and the reason
it can is the same reason the loop is safe.

### Work breakdown (MECE)

1. **Grammar** (`bajutsu/common/scenario/models/`). The `Repeat` model, the `times` XOR `while`
   validator, the 1–100 caps, `maxIterations` required, and
   [dsl-grammar](../../docs/dsl-grammar.md) §2 / §4 / §5 with the Japanese mirror.
2. **Condition-evaluation hoist**. `_eval_condition` shared by `_run_if`, `_run_repeat`, and the
   interrupt guard, with `if`'s existing behaviour proven unchanged.
3. **`_run_repeat` and dispatch**. Both forms, the `as` binding, fail-at-bound with the count in the
   reason, and `_StepCounter` nesting.
4. **Preflight walk**. `_walk_steps` recurses into `repeat.steps`, with a test that an unsupported
   step inside a loop is rejected before any device work.
5. **Static-analysis walks**. `audit` (selectors, findings, the `loose-loop` finding), `coverage`,
   and `trace`.
6. **Codegen**. `times` emitted by all three targets; `while` refused loudly.
7. **Documentation and fixtures**. [scenarios](../../docs/scenarios.md) authoring section, the
   `audit` finding row in [cli](../../docs/cli.md), a showcase scenario for each form, and the
   Japanese mirrors.

### Prime directives preserved

- **No LLM on the run path.** The condition is the same machine-checkable assertion `if` already
  evaluates. The verdict still comes from `expect` assertions alone.
- **Determinism.** The grammar cannot express a loop that fails to terminate, and reaching the bound
  is a failure rather than a quiet exit, so a scenario cannot go green having done less than it
  asked.
- **App-agnostic.** `repeat` needs nothing a backend might lack, and no capability token is added.
  The body's own steps are gated exactly as they are today.
- **Codegen.** `times` translates faithfully; `while` refuses loudly rather than degrading into a
  fixed count that would check something the scenario never asked for.

## Alternatives considered

- **An unbounded `while`.** Rejected on two independent grounds. BE-0033 already ruled it out,
  because a scenario that can diverge makes pass/fail depend on logic the runner cannot bound. And
  the practical failure is worse than a slow test: a diverging run is killed by a continuous
  integration wall-clock timeout, which produces **no verdict at all** rather than a fail. It lands
  in the run history as a hole, which is the one shape `flakiness` and `audit --history` cannot
  analyse around.
- **A `times:` modifier on any step**, as in `tap: {...}` plus `times: 5`. Rejected: it breaks the
  exactly-one-action-key rule `Step` enforces, gives no place for a shared iteration variable, and
  cannot express a multi-step body — so an author needing two steps repeated is back where they
  started.
- **Unroll `times` in the loader**, expanding into N copies alongside `expand_components` and
  `expand_data`. Tempting, since static analysis would need no change and the runtime none. Rejected
  for two reasons. The report would show N indistinguishable steps rather than one loop with N
  iterations, so a reader could not tell an intentional repetition from a copy-paste mistake. And it
  cannot express `while` at all, so the grammar would carry two unrelated mechanisms for one concept.

## Progress

> Keep this current as work proceeds. The checklist mirrors the MECE work breakdown in
> *Detailed design* (one box per unit of work); the log records what changed and when
> (oldest first), linking the PRs.

- [ ] Grammar — the `Repeat` model, its validators, the caps, and the DSL grammar.
- [ ] Condition-evaluation hoist — `_eval_condition` shared by three callers.
- [ ] `_run_repeat` and the dispatch arm, with fail-at-bound and step nesting.
- [ ] Preflight walk into `repeat.steps`, proven by a fail-fast test.
- [ ] Static-analysis walks — `audit`, `coverage`, `trace`, and the `loose-loop` finding.
- [ ] Codegen — `times` emitted, `while` refused.
- [ ] Documentation and a showcase scenario for each form.

Open questions to settle while building:

- The 100 ceiling. Whether it is right, and whether it should be configurable per target. A
  configurable ceiling weakens the argument that the grammar itself bounds the loop, so the current
  position is a hard constant.
- `as` binds a string, matching the existing bindings map. Whether a numeric use case justifies
  widening that map is a separate decision.
- Whether a `while` loop that exits because its condition became false should record the iteration
  count in the manifest. It would help diagnose a loop that ran once where the author expected five,
  at the cost of new manifest surface.
- How an interrupt firing inside a loop body interacts with recovery suppression across iterations.

## References

- [BE-0033 — Scenario variables + light control flow](../BE-0033-scenario-variables-control-flow/BE-0033-scenario-variables-control-flow.md)
  — shipped `if` and `forEach`, named this gap, and rejected the unbounded form this item does not
  propose.
- [BE-0326 — The `scroll` action: scroll until an element appears](../BE-0326-scroll-to-element/BE-0326-scroll-to-element.md)
  and [BE-0400 — Make a scroll step travel the distance it asks for](../BE-0400-scroll-step-amount/BE-0400-scroll-step-amount.md)
  — `maxScrolls`, the author-stated bound and fail-at-a-bound precedent this generalizes.
- [BE-0082 — Preflight capability check before a run](../BE-0082-capability-preflight-check/BE-0082-capability-preflight-check.md)
  — why the preflight walk must recurse into a loop body.
- [BE-0297 — Expand XCUITest codegen's real-compile coverage](../BE-0297-codegen-xcuitest-dsl-coverage/BE-0297-codegen-xcuitest-dsl-coverage.md)
  — the runtime-only refusal `while` joins.
- `bajutsu/common/orchestrator/loop.py` (`_run_if`, `_run_for_each`, the step dispatch),
  `bajutsu/common/capability/capability_preflight.py` (`_walk_steps`),
  `bajutsu/codegen/common.py` (`_reject_runtime_only`).
