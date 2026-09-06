**English** · [日本語](BE-XXXX-mcp-agent-working-loop-ja.md)

# BE-XXXX — Expose the whole Claude-free command set over MCP, with structured returns

<!-- BE-METADATA -->
| Field | Value |
|---|---|
| Proposal | [BE-XXXX](BE-XXXX-mcp-agent-working-loop.md) |
| Author | [@0x0c](https://github.com/0x0c) |
| Status | **Proposal** |
| Tracking issue | [Search](https://github.com/bajutsu-e2e/bajutsu/issues?q=is%3Aissue+label%3Aroadmap-tracking+in%3Atitle+"BE-XXXX") |
| Topic | Integration & automation |
| Related | [BE-0017](../BE-0017-mcp-server/BE-0017-mcp-server.md), [BE-0018](../BE-0018-evidence-as-mcp-resources/BE-0018-evidence-as-mcp-resources.md), [BE-0301](../BE-0301-mcp-real-wire-protocol-test/BE-0301-mcp-real-wire-protocol-test.md), [BE-0101](../BE-0101-ai-free-zero-config/BE-0101-ai-free-zero-config.md), [BE-0330](../BE-0330-scenario-authoring-skill/BE-0330-scenario-authoring-skill.md), [BE-0049](../BE-0049-determinism-flakiness-audit/BE-0049-determinism-flakiness-audit.md), [BE-0174](../BE-0174-scenario-ref-path-containment/BE-0174-scenario-ref-path-containment.md) |
<!-- /BE-METADATA -->

## Introduction

The MCP server exposes two tools — `bajutsu_run` and `bajutsu_doctor`
(`bajutsu/mcp/tools.py:54`, `:82`) — against a command surface of twenty. Both return a rendered
string. An agent connected over the Model Context Protocol (MCP) can therefore start an expensive
device run and score a screen, but cannot validate a draft, read the grammar, or grade what it wrote.
This item exposes the Claude-free command set through the classification that already enumerates it,
and returns structured data where the command already computes it.

## Motivation

The five things an agent does while authoring a scenario are: read the grammar, draft, validate the
draft, grade the selectors it chose, and — after a run — read the failure. Over MCP it can do the
fourth-from-last only by starting a device run, and the rest not at all. So the agent falls back to a
shell: it writes the draft to a file, runs `bajutsu lint <path>`, and reads the words `ok` off
standard output. Every one of those steps is a place the MCP integration was supposed to remove.

The fallback is not merely inelegant; it is weaker than what the library already offers.
`lint_text(text)` (`bajutsu/cli/commands/lint.py:28`) validates a scenario **from its text**. An
agent could hand over a draft it has not written to disk yet and get the errors back — the tightest
possible authoring loop. Going through the shell forces a file to exist before it is known to be
valid, which is exactly backwards.

The returns are the second half of the problem. `bajutsu_run` returns `"PASS  <manifest>"` with
standard error appended (`:130-133`), and `bajutsu_doctor` returns `render(s)` (`:80`) — the
human-formatted grade. An agent parses prose to learn what a dataclass already knew. Six commands
already emit JSON behind a `--json` flag — `audit`, `coverage`, `impact`, `stats`, `flakiness`,
`triage` — so for those the structure exists and the MCP layer discards it.

There is a ready-made rule for *which* commands belong here, and it is already load-bearing.
[BE-0101](../BE-0101-ai-free-zero-config/BE-0101-ai-free-zero-config.md)'s `CAPABILITIES` table
(`bajutsu/common/capability/capabilities.py:41`) classifies every command exactly once as
Claude-using or Claude-free, and `test_classification_matches_the_registered_command_set_exactly`
(`tests/test_capabilities.py:24`) fails when a newly added command is left unclassified. The
Claude-free set is precisely the set an agent may call without putting a second model on the path.

Once this ships, a reader can check it from an agent session with no shell access: the agent
validates a draft it has not saved, reads the JSON Schema, grades its own selectors, and reads a
manifest — four steps that today each require a terminal. `bajutsu audit` over MCP returns the same
finding objects `--json` prints, not a paragraph about them.

## Detailed design

### The exposure table, and why it is a table rather than a rule

"Expose every Claude-free command" is nearly right and wrong in three places. `serve`, `worker`, and
`mcp` are Claude-free and are long-running servers: a tool call that never returns is not a tool. So
the selection is an explicit table in `bajutsu/mcp/`, one row per command, each row carrying either
the tool it becomes or the reason it becomes none:

- **Exposed, device-free** — `lint`, `schema`, `audit`, `coverage`, `impact`, `stats`, `flakiness`,
  `trace`, `report`, `export`, `codegen`. These are the authoring loop.
- **Exposed, evidence-shaped** — `approve`, which promotes a run's captured screenshots to visual
  baselines and so reads a run directory rather than a device.
- **Exposed, device-using** — `run` and `doctor`, already present.
- **Not exposed, with a recorded reason** — `serve`, `worker`, `mcp` (long-running servers);
  `record` and `crawl` (Claude-using — exposing them would put a model behind a tool call the
  calling agent believes is deterministic); `triage` exposed only on its Claude-free default path,
  with `--ai` unavailable, mirroring how `CAPABILITIES` records the flag that flips it.

A test asserts the table covers `CAPABILITIES` exactly, in the shape of the existing completeness
test. A new command then forces two decisions in two places, each recorded: is it Claude-free, and
is it an MCP tool.

### Structured returns

Each exposed tool returns the structure its command already computes, serialized once at the MCP
boundary:

- The six commands with `--json` return the same objects that flag serializes. The MCP tool calls
  the analysis function directly rather than the CLI, so the flag's rendering is not re-parsed.
- `lint` returns `{ok, errors, provenanceCoverage}` — the list `lint_text` already returns, plus the
  BE-0044 advisory the CLI prints separately.
- `doctor` returns the `score()` dataclass rather than `render()`'s text. The rendered form stays
  available as a field, so an agent that wants to show a human the familiar grade still can.
- `run` keeps its verdict but returns it as `{verdict, manifest, runId, stderr}` rather than a line
  to be split. `_parse_verdict` (`:28`) exists because the MCP layer re-parses `run`'s own stdout; a
  tool that calls the runner in-process would not need it. That is a larger change than this item
  wants to force, so `run`'s internals stay as they are and only the return shape is structured —
  and the docstring says why the parse is still there.

### Text in, not just paths in

`bajutsu_lint` takes `scenario_text` or `scenario_path`, exactly one of the two.
`load_scenario_file(text)` and `lint_text(text)` already accept text, so the text path costs a
parameter, not a mechanism. This is the difference between an agent that can check a draft and an
agent that must commit it to the filesystem first.

`bajutsu_codegen` takes text the same way. `bajutsu_audit`'s static mode does too; its `--repeat`
and `--history` modes need a target and a runs directory and so stay path-shaped.

### Path containment, reused rather than reinvented

Every path parameter an agent supplies is untrusted in the same way a resource URI is. The resource
handlers already confine reads to the runs root (`bajutsu/mcp/resources.py:12-48`), and
[BE-0174](../BE-0174-scenario-ref-path-containment/BE-0174-scenario-ref-path-containment.md)
established containment for scenario references. The new tools reuse both rather than growing a
third rule: a scenario path is contained the way BE-0174 contains a `ref`, and a runs path the way
`_run_base` contains a `run_id`.

### The boundary this does not move

Every tool here is Tier-1: the agent authors and investigates, and the deterministic gate is
untouched. `run`'s verdict still comes from machine-checkable assertions. Exposing more read-only
analysis to an agent does not put a model on the verdict path, and the exclusion of `record` and
`crawl` is what keeps a *second* model from appearing behind a tool call the calling agent takes to
be deterministic.

### Its relationship to the authoring skill

[BE-0330](../BE-0330-scenario-authoring-skill/BE-0330-scenario-authoring-skill.md) proposes a Claude
Code skill that drafts scenarios from source and self-validates them. The two are complementary and
should be built in this order: BE-0330 describes *what an agent should do*, and this item supplies
*the calls it makes*. A skill that must shell out for validation is a skill that only works where a
shell and a checkout exist. If BE-0330 lands first, it should be written against the shell path and
migrated; the two items should not each grow their own validation route.

### Work breakdown (MECE)

1. **The exposure table** and its completeness test against `CAPABILITIES`.
2. **Structured return types** — one model per tool, and the serialization at the boundary.
3. **The device-free authoring tools** — `lint`, `schema`, `audit`, `codegen`, with text-or-path
   input.
4. **The evidence tools** — `coverage`, `impact`, `stats`, `flakiness`, `trace`, `report`, `export`,
   and `approve`, reading the runs root the resources already root themselves at.
5. **The device tools** — the restructured returns for the existing `run` and `doctor`.
6. **Path containment** for every new path parameter, reusing the resource and BE-0174 rules.
7. **Wire-protocol coverage** — extending
   [BE-0301](../BE-0301-mcp-real-wire-protocol-test/BE-0301-mcp-real-wire-protocol-test.md)'s
   round-trip test to the new tools, so the schemas are exercised over a real transport rather than
   by calling the Python functions.
8. **Documentation** — the tool table in the MCP reference and its Japanese mirror, and a note on
   which commands are deliberately absent.

## Alternatives considered

- **A single `bajutsu_cli` tool taking a command line.** Rejected: it gives an agent a shell by
  another name, with no schema, no containment, and no way to keep `record`, `crawl`, and
  `triage --ai` out — the classification BE-0101 made load-bearing would stop being enforceable at
  this boundary. Its one real advantage, that a new command needs no MCP work, is the same property
  that lets a new command arrive unclassified.
- **Expose everything as MCP resources rather than tools.** Rejected: a resource is addressed by
  URI and read; these calls take arguments (a target, a scenario text, a repeat count) and have
  effects worth an approval prompt. BE-0018 already put the read-only evidence on the resource side,
  which is where it belongs; this item is the other half.
- **Keep string returns and document the format.** Rejected: a documented string format is a parser
  contract with none of a schema's enforcement, and the repository has already met its cost —
  `_parse_verdict` exists to re-parse a format `run` itself produced, and its docstring explains at
  length which line to trust. Adding more such formats spends the same cost repeatedly.
- **Generate the tools from the Typer app by introspection.** Genuinely attractive: one registration
  and no table to maintain. Rejected: it would expose whatever is registered, including the servers
  and the Claude-using commands, and would derive each tool's schema from CLI options — which encode
  a terminal's conventions (`--json`, `--udid "booted"`) rather than what an agent needs. The
  explicit table is the place a decision gets recorded; introspection is the place decisions go
  missing.

## Progress

> Keep this current as work proceeds. The checklist mirrors the MECE work breakdown in
> *Detailed design* (one box per unit of work); the log records what changed and when
> (oldest first), linking the PRs.

- [ ] The exposure table and its completeness test.
- [ ] Structured return types at the MCP boundary.
- [ ] The device-free authoring tools, with text-or-path input.
- [ ] The evidence tools.
- [ ] The restructured `run` / `doctor` returns.
- [ ] Path containment for every new path parameter.
- [ ] Wire-protocol coverage for the new tools.
- [ ] Documentation in both languages.

Open questions to settle while building:

- Whether the structured returns are a breaking change for an existing agent configuration, and
  whether the first release should return both shapes. The server has no published version today,
  which argues for changing cleanly now.
- Whether `run` over MCP should stream progress. The protocol supports it; the current tool blocks
  for up to ten minutes (`bajutsu/mcp/tools.py:121`), which an agent experiences as a hang.
- Whether `codegen` belongs here at all, given that its output is a file an agent could write
  itself. The argument for including it is that the emitters encode which fields each target
  rejects, and an agent guessing at that produces code that will not compile.

## References

- [BE-0017 — MCP server](../BE-0017-mcp-server/BE-0017-mcp-server.md) and
  [BE-0018 — Return evidence as MCP resources](../BE-0018-evidence-as-mcp-resources/BE-0018-evidence-as-mcp-resources.md)
  — the two tools and the resource surface this item extends.
- [BE-0301 — Real wire-protocol round-trip test for the MCP server](../BE-0301-mcp-real-wire-protocol-test/BE-0301-mcp-real-wire-protocol-test.md)
  — the test harness each new tool's schema must pass through.
- [BE-0101 — Legible Claude-using / Claude-free split with a zero-config non-AI path](../BE-0101-ai-free-zero-config/BE-0101-ai-free-zero-config.md)
  — the classification that decides which commands may be exposed.
- [BE-0330 — Ship a Claude Code skill that drafts and self-validates scenarios from source](../BE-0330-scenario-authoring-skill/BE-0330-scenario-authoring-skill.md)
  — the skill that would otherwise shell out for the calls this item defines.
- [BE-0049 — Determinism / flakiness audit](../BE-0049-determinism-flakiness-audit/BE-0049-determinism-flakiness-audit.md)
  — `audit`'s three modes, two of which stay path-shaped over MCP.
- [BE-0174 — Contain scenario component and data refs within the suite root](../BE-0174-scenario-ref-path-containment/BE-0174-scenario-ref-path-containment.md)
  — the containment rule the new scenario-path parameters reuse.
- `bajutsu/mcp/tools.py` (`:28` the verdict re-parse, `:54`/`:82` the two tools),
  `bajutsu/mcp/resources.py:12-48` (path containment),
  `bajutsu/common/capability/capabilities.py:41`, `tests/test_capabilities.py:24`.
