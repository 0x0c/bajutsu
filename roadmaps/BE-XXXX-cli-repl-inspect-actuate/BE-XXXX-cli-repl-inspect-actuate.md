**English** · [日本語](BE-XXXX-cli-repl-inspect-actuate-ja.md)

# BE-XXXX — Interactive REPL for element-tree inspection and id-based actuation

<!-- BE-METADATA -->
| Field | Value |
|---|---|
| Proposal | [BE-XXXX](BE-XXXX-cli-repl-inspect-actuate.md) |
| Author | [@0x0c](https://github.com/0x0c) |
| Status | **Proposal** |
| Tracking issue | [Search](https://github.com/bajutsu-e2e/bajutsu/issues?q=is%3Aissue+label%3Aroadmap-tracking+in%3Atitle+"BE-XXXX") |
| Topic | Authoring experience |
<!-- /BE-METADATA -->

## Introduction

`bajutsu repl` opens a manual command shell against a running target. An operator launches the
app once, then types one command at a time. `tree` reads the current screen's element tree.
`tap <id>` acts on one of its elements. Each result is read before the next command is chosen. The
shell sits beside `record` (goal-directed AI authoring) and `crawl` (autonomous exploration) as a
third way to reach a target through the same
[`Driver`](../../docs/glossary.md#driver-backend-actuator-platform) interface those two commands
already use. Unlike `record` and `crawl`, `repl` asks no large language model (LLM) anything and
writes no scenario. `repl` is a thin loop over `query()` and the actuation methods every
[backend](../../docs/glossary.md#driver-backend-actuator-platform) already implements, so
XCUITest, adb, and Playwright gain the shell for free with no per-backend code.

## Motivation

Finding out which [selector](../../docs/glossary.md#scenario-authoring) will resolve to which
element costs more than the question deserves today. An operator can read the tree by eye in
Xcode's Accessibility Inspector, or in a browser's devtools. That reading is backend-specific.
It also skips the normalized `id` / `label` / `traits` fields a scenario step actually matches
against. The alternative inside Bajutsu is `record` or `crawl`. Both drive the app through an AI
call, and both produce output shaped for their own artifact — a scenario, a screen map — rather
than one query answered right away. None of the three gives a direct, backend-agnostic answer to
one question: what does the current screen look like, and what happens when one of its ids is
tapped.

`repl` answers that question directly. `tree` prints the current element tree. `tap <id>` acts on
one of its elements. A second `tree` shows what changed, with no AI round trip, no scenario file,
and no per-backend inspector to learn. A selector that fails to match during authoring is a
common outcome: the id carries a typo, another element covers it, or it appears after a wait.
Diagnosing that today means writing a candidate scenario step, running it, and reading the
manifest's captured tree afterward. `repl` shortens that loop to typing `tree` and `tap` against a
running app. Once this ships, an operator launches `bajutsu repl --target <name>`, runs `tree`,
reads the visible elements' ids, taps one of them, and watches the screen change. That loop takes
seconds, in place of a run-and-read-the-report cycle.

## Detailed design

`bajutsu repl --target <name> [--udid <id>] [--backend <list>] [--erase/--no-erase] [--config
<path>]` launches the app. It reuses the `launch_driver` helper `record` and `crawl` already call
(`bajutsu/common/runner/launch.py`). Target resolution, device selection, and backend selection
therefore behave the same as for those two commands. On launch, `repl` prints the resolved
backend and target, then a `bajutsu>` prompt.

The v1 command set stays small and id-first:

| Command | Behavior |
|---|---|
| `tree [--json]` | `driver.query()`, rendered as a table of `id` / `label` / `traits` / `value` / `frame` (or as JSON) |
| `find <substring>` | the same tree, filtered to rows whose `id` or `label` contains `<substring>` |
| `tap <id>` | `driver.tap({"id": "<id>"})` |
| `type <id> <text>` | tap `<id>` to focus it, then `driver.type_text("<text>")` |
| `back` | `driver.back()` |
| `screenshot [path]` | `driver.screenshot(path)`, auto-named when `path` is omitted |
| `help` | list the commands above |
| `exit` / `quit` | leave the shell; the app keeps running rather than getting torn down |

Every command that reads or resolves against the tree reuses the settled-read path `run` already
relies on. The read-lag barrier
([BE-0332](../../roadmaps/BE-0332-read-lag-barrier/BE-0332-read-lag-barrier.md)) keeps a `tree`
issued right after a `tap` from reading a stale, pre-actuation snapshot. `resolve_unique`'s
existing zero-or-many-matches contract fails a command right away with the same
`ElementNotFound` / `AmbiguousSelector` message `run` would raise. Neither path guesses which
element the operator meant (prime directive 2 — determinism first).

`tap` and `type` address an element by `id` alone. That is narrower than the full
[selector](../../docs/glossary.md#scenario-authoring) syntax `run` accepts, on purpose: it keeps
this first version small enough to review, and it matches how the shell gets used. `tree` already
shows every element's `label` and `traits`, so an operator reads the row and types its id. An
element with no `id` still appears in `tree`, but `repl` cannot act on it in v1. Closing that gap
is `crawl`'s vision fallback's job, and `repl` does not attempt it: adding vision would put an AI
call back into a tool built to avoid one. Extending `tap` and `type` to the rest of the selector
syntax (`label`, `labelMatches`, `index`) is a natural follow-up, scoped separately, once the
shell itself has shipped.

Gestures (`swipe`, `scroll`, `pinch`, `rotate`) and platform-specific actions (`set_picker_value`,
`select_option`) stay out of v1. `tap`, `type_text`, `back`, and `screenshot` cover what an
operator reaches for first when confirming a selector or walking a flow by hand. The remaining
`Driver` methods are plain additions once the command-parsing shape is settled. Adding every one
of them at once would widen this item past a single reviewable change.

## Alternatives considered

- **Read the tree with a platform-native tool** (Xcode's Accessibility Inspector, browser
  devtools). Rejected: each tool is backend-specific, which works against keeping the tool
  [app-agnostic](../../docs/glossary.md#driver-backend-actuator-platform) (prime directive 3).
  None of them shows the normalized `id` / `label` / `traits` fields a Bajutsu selector matches
  against, so an id read there is not guaranteed to be the id `run` would resolve.
- **Add a "manual mode" flag to `record` instead of a new command.** Rejected: `record`'s loop is
  built around `ClaudeAgent` proposing actions from a screenshot, and it always ends by writing a
  scenario. Bolting a human-typed command path onto that loop would tangle an AI-driven path and a
  non-AI one in one module. `repl` never writes a scenario, on purpose, so a separate command
  keeps both simpler to read.
- **Accept a full selector (`label`, `labelMatches`, `index`) for `tap`/`type` from the start.**
  Rejected for v1 in favor of id-only addressing (see *Detailed design*). The smaller surface
  already answers the question behind this item, and it lands as one reviewable change rather
  than one that also has to settle selector-syntax parsing on a command line.
- **A non-interactive mode that reads commands from stdin or a file.** Rejected for this item. The
  interactive shell alone proves the command set before any scripting surface gets built on top
  of it. A batch mode is a follow-up, scoped separately, once that command set is settled.

## Progress

> Keep this current as work proceeds. The checklist mirrors the MECE work breakdown in
> *Detailed design* (one box per unit of work); the log records what changed and when
> (oldest first), linking the PRs.

- [ ] `bajutsu repl` command scaffold: `launch_driver` reuse, the `bajutsu>` prompt loop, `help` /
  `exit` / `quit`.
- [ ] `tree` / `tree --json` / `find <substring>`, reusing the settled-read / read-lag-barrier
  query path.
- [ ] `tap <id>` / `type <id> <text>`, surfacing `ElementNotFound` / `AmbiguousSelector` the same
  way `run` does.
- [ ] `back` / `screenshot [path]`.
- [ ] `docs/cli.md` and `docs/ja/cli.md` reference sections.

## References

- [`Driver`](../../docs/glossary.md#driver-backend-actuator-platform) protocol —
  `bajutsu/common/drivers/base/driver.py`
- [`Selector`](../../docs/glossary.md#scenario-authoring) — `bajutsu/common/scenario/models/selector.py`
- `record` and `crawl` — the two existing Tier 1 authoring paths `repl` sits beside (`docs/cli.md`)
- [BE-0332 — read-lag barrier](../../roadmaps/BE-0332-read-lag-barrier/BE-0332-read-lag-barrier.md)
