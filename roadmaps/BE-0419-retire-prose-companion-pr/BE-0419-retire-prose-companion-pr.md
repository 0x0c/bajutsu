**English** · [日本語](BE-0419-retire-prose-companion-pr-ja.md)

# BE-0419 — Retire the prose companion-PR mechanism; fix wording findings in the source PR

<!-- BE-METADATA -->
| Field | Value |
|---|---|
| Proposal | [BE-0419](BE-0419-retire-prose-companion-pr.md) |
| Author | [@0x0c](https://github.com/0x0c) |
| Status | **Implemented** |
| Tracking issue | [Search](https://github.com/bajutsu-e2e/bajutsu/issues?q=is%3Aissue+label%3Aroadmap-tracking+in%3Atitle+"BE-0419") |
| Implementing PR | [#1983](https://github.com/bajutsu-e2e/bajutsu/pull/1983) |
| Topic | Contributor workflow |
| Related | [BE-0343](../BE-0343-prose-companion-pr/BE-0343-prose-companion-pr.md), [BE-0203](../BE-0203-claude-code-pr-review/BE-0203-claude-code-pr-review.md) |
<!-- /BE-METADATA -->

## Introduction

Bajutsu's advisory pull-request reviewer (BE-0203) runs two wording-only lenses: Japanese prose
quality, and its English `docs/*.md`-and-roadmap-prose counterpart. BE-0343 gave each finding from
those two lenses a `(non-blocking, prose)` decoration and a dedicated `prose-companion` job that
mechanically applied the finding's own `suggestion` block to a `prose-fix/pr-<N>` branch, then opened
a small pull request against the contributor's own branch — so a wording fix never re-ran the
contributor's full CI matrix. This item retires that job, the script behind it
(`scripts/prose_companion_pr.py`), and its tests. Both prose lenses keep flagging a genuine
violation, and a finding still carries a `suggestion` block wherever the fix is mechanical, but the
decoration drops to the plain `(non-blocking)` every other finding already carries, and the fix
lands as an ordinary push to the pull request that raised it — the same way a contributor already
answers any other review comment.

## Motivation

BE-0343 existed to solve one problem: pushing a fix for a pure-wording finding to the same pull
request re-ran that pull request's entire CI matrix, for a change with no behavioral risk. A
companion pull request avoided that cost by shipping the fix on its own small branch, reviewable
while the source pull request stayed open.

That benefit came with an ongoing cost the original proposal weighed against the CI-cycle savings at
the time: a privileged automation identity with write access to a contributor's own branch, a job
with its own trust guards and no-op paths, a script exercised only when a wording finding happens to
appear, and a second pull request contributors now have to notice, review, and merge separately from
the one they are actually working on. A companion pull request is never free to review, even
when applying its own suggested text takes one click.

Weighed against the occasional CI-cycle cost it exists to avoid, the standing machinery — the
privileged identity, the extra job, the script, and the second pull request every contributor must
separately track — is the heavier cost of the two. This item removes it and returns to a plainer
rule: a wording-only finding is a review comment like any other, fixed with a normal push. A reader
can tell this held once no new `prose-fix/pr-<N>` branch or pull request appears after a wording
finding, and the fix instead arrives as the contributor's own push to their own pull request.

## Detailed design

### What changes

- [`.github/claude-review-prompt.md`](../../.github/claude-review-prompt.md) drops the "Mark a
  wording-only finding `(non-blocking, prose)`" bullet and the `(non-blocking, prose)` decoration
  itself. A finding from either prose lens keeps the plain `(non-blocking)` decoration and, wherever
  the fix is mechanical, a `suggestion` block — the same treatment every other finding already gets.
  The "Prose-quality conventions" section keeps both lenses at their existing bar (a clear, nameable
  violation with a concrete rewrite), but its rationale no longer cites a free fix: the bar stays
  because a `suggestion` block already makes the rewrite a one-line apply, and because these two
  lenses are the review's only automated check on the `document-writing` prose norms
  [`CLAUDE.md`](../../CLAUDE.md) already requires.
- [`.github/workflows/claude-review.yml`](../../.github/workflows/claude-review.yml) drops the
  `prose-companion` job entirely. The `review` job (BE-0203, narrowed to open/reopen and
  `@claude review` by [BE-0347](../BE-0347-bounded-ci-review-cycle/BE-0347-bounded-ci-review-cycle.md))
  is unchanged.
- This item deletes `scripts/prose_companion_pr.py` and `tests/test_prose_companion_pr.py`.
- `tests/test_claude_review_workflow.py` drops its `prose-companion`-job assertions, and its module
  docstring's mention of them, keeping only what still describes the `review` job's own trigger
  wiring.
- [`.apm/skills/claude-review/SKILL.md`](../../.apm/skills/claude-review/SKILL.md) drops the
  marker-posting instructions (its step 3 scope note and step 5 posting format), and `make skills`
  syncs the deployed `.claude/skills/claude-review/SKILL.md` copy.
- [`CLAUDE.md`](../../CLAUDE.md) drops the "a wording-only review finding arrives as a companion PR"
  bullet. [`docs/ai-development.md`](../../docs/ai-development.md) and its
  [`docs/ja/ai-development.md`](../../docs/ja/ai-development.md) mirror drop "The companion PR for
  wording-only findings (BE-0343)" section, replaced by a short paragraph next to the advisory
  reviewer's own description: a wording-only finding is fixed like any other, with a normal push to
  the same pull request.

### What does not change

- Both prose lenses' judging scope and severity floor in `.github/claude-review-prompt.md`.
- The `review` job itself, and everything BE-0347 governs about when it runs.
- `roadmaps/BE-0343-prose-companion-pr/` stays `Implemented` — that was, and remains, an accurate
  record of what shipped. It now also carries a `Superseded by` link to this item.

### The three companion pull requests already open

At the time of writing, three companion pull requests are still open — #1978, #1980, and #1982 —
each based on a still-open source pull request. Removing the job does not touch them: each stays an
ordinary pull request a maintainer can review and merge like any other small change, or close if its
source pull request no longer needs it. No new companion pull request opens once this item merges.

## Alternatives considered

- **Keep the mechanism, but gate it further (for example, an on-demand `@claude prose-pr`
  comment).** BE-0343's own proposal already rejected an on-demand trigger, since it reintroduces a
  manual step. Narrowing the automatic trigger the same way here would still leave every piece of
  standing machinery in place, so it removes none of the cost this item exists to retire.
- **Drop only the `(non-blocking, prose)` marker and leave the job in place, dormant.** A job no
  finding ever reaches is dead code that still carries a live GitHub App identity and its own test
  suite to keep passing. Deleting it is no more work than leaving it, and it leaves nothing to
  explain to a later reader.
- **Drop the two prose lenses entirely, instead of only the companion-PR delivery.** Nothing here
  suggests the two lenses' underlying judgment has become less valuable; only shipping the fix
  through a second pull request has stopped paying for itself. Removing the lenses too would quietly
  lower the review's coverage of the `document-writing` house convention that
  [`CLAUDE.md`](../../CLAUDE.md) still requires.

## Progress

> Keep this current as work proceeds. The checklist mirrors the MECE work breakdown in
> *Detailed design* (one box per unit of work); the log records what changed and when
> (oldest first), linking the PRs.

- [x] Remove the `(non-blocking, prose)` marker and rewrite the "Prose-quality conventions"
  rationale in `.github/claude-review-prompt.md`
- [x] Remove the `prose-companion` job from `.github/workflows/claude-review.yml`
- [x] Delete `scripts/prose_companion_pr.py` and `tests/test_prose_companion_pr.py`; trim
  `tests/test_claude_review_workflow.py`
- [x] Drop the marker-posting instructions from `.apm/skills/claude-review/SKILL.md` and sync
  `.claude/skills/claude-review/SKILL.md` with `make skills`
- [x] Update the `CLAUDE.md` bullet and the `docs/ai-development.md` / `docs/ja/ai-development.md`
  sections
- [x] Add the reciprocal `Superseded by` link on `roadmaps/BE-0343-prose-companion-pr/` once this
  item's id is allocated

### Log

- Shipped whole, in the same pull request that proposed it
  ([`propose-and-build`](../../.apm/skills/propose-and-build/SKILL.md)). Three companion pull
  requests were already open at the time (#1978, #1980, #1982); they are left as ordinary,
  independently mergeable pull requests rather than closed.
- Added the reciprocal `Superseded by` link on `roadmaps/BE-0343-prose-companion-pr/` now that this
  item's id (`BE-0419`) is allocated.

## References

[BE-0343](../BE-0343-prose-companion-pr/BE-0343-prose-companion-pr.md) (the mechanism this item
retires); [BE-0203](../BE-0203-claude-code-pr-review/BE-0203-claude-code-pr-review.md) (the advisory
reviewer both prose lenses belong to); [BE-0347](../BE-0347-bounded-ci-review-cycle/BE-0347-bounded-ci-review-cycle.md)
(the trigger narrowing the `review` job keeps); the `document-writing`, `english-document-writing`,
and `japanese-document-writing` skills (the norms behind both prose lenses).
