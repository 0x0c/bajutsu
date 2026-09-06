**English** · [日本語](BE-XXXX-publish-package-pypi-ja.md)

# BE-XXXX — Publish the package with a real version and a release workflow

<!-- BE-METADATA -->
| Field | Value |
|---|---|
| Proposal | [BE-XXXX](BE-XXXX-publish-package-pypi.md) |
| Author | [@0x0c](https://github.com/0x0c) |
| Status | **Proposal** |
| Tracking issue | [Search](https://github.com/bajutsu-e2e/bajutsu/issues?q=is%3Aissue+label%3Aroadmap-tracking+in%3Atitle+"BE-XXXX") |
| Topic | CI / build infrastructure |
| Related | [BE-0292](../BE-0292-xcuitest-bundled-runner/BE-0292-xcuitest-bundled-runner.md), [BE-0272](../BE-0272-serve-version-badge/BE-0272-serve-version-badge.md), [BE-0277](../BE-0277-docker-build-commit-badge/BE-0277-docker-build-commit-badge.md), [BE-0111](../BE-0111-ai-sdk-optional-dependency/BE-0111-ai-sdk-optional-dependency.md), [BE-0119](../BE-0119-scenario-schema-versioning/BE-0119-scenario-schema-versioning.md), [BE-0164](../BE-0164-config-aware-environment-installer/BE-0164-config-aware-environment-installer.md), [BE-0173](../BE-0173-slim-web-worker-image/BE-0173-slim-web-worker-image.md) |
<!-- /BE-METADATA -->

## Introduction

The package is not published, and `pyproject.toml` carries `version = "0.0.0"` (`:3`), duplicated in
`bajutsu/__init__.py` (`:3`). This item makes the install instruction the documentation already gives
into a true one: a single-source version, a tag-triggered release workflow publishing over OpenID
Connect trusted publishing, a `bajutsu --version` flag, and a decision for each artifact that cannot
live in a pure-Python wheel.

## Motivation

[README](../../README.md) (`:167`) and the [getting-started guide](../../docs/getting-started/index.md)
(`:49`) both instruct `pip install bajutsu`, and go on to describe what the base install does and does
not carry. Neither instruction works. Every evaluation therefore starts with a clone and a
toolchain, and the documentation's first concrete step is one a reader cannot take.

The absence has already degraded shipped work twice.
[BE-0272](../BE-0272-serve-version-badge/BE-0272-serve-version-badge.md)'s version badge renders
`0.0.0`, because nothing ever fills the field it reads.
[BE-0277](../BE-0277-docker-build-commit-badge/BE-0277-docker-build-commit-badge.md) exists at all
because BE-0272 had to defer build-time stamping — there was no build pipeline to hook into.

Four optional extras are self-referential: `bedrock` (`:31`), `worker-web` (`:41`), `worker-ios`
(`:45`), and `cloud` (`:70`) each declare a dependency on `bajutsu[…]`. A self-referential extra
resolves for an outside user only once the distribution is findable by name, so
`pip install 'bajutsu[worker-web]'` cannot work for anyone today, however correct the declaration is.

Once this ships, a reader can check it from a machine with no clone of this repository:
`pip install bajutsu && bajutsu --version && bajutsu lint <file>` succeeds and prints a version that
is not `0.0.0`. Two shipped features stop showing a placeholder at the same time — the `serve` header
badge, and a self-hosted image's version field.

## Detailed design

### Versioning, and what the number promises

Semantic Versioning from **`0.1.0`**, pre-1.0, with one thing recorded explicitly: the scenario
grammar's compatibility promise is carried by `schema:`
([BE-0119](../BE-0119-scenario-schema-versioning/BE-0119-scenario-schema-versioning.md)), **not** by
the package version. That separation matters. A minor bump may change a command-line flag, but only a
`schema` bump makes an older Bajutsu refuse a newer scenario file rather than misread it. Writing it
down stops a later reader inferring a stronger promise from the version number than the tool makes.

### One source for the version

The string exists twice today and the two can drift silently. `pyproject.toml` declares
`dynamic = ["version"]` with `[tool.hatch.version]` pointing at `bajutsu/__init__.py`, so the literal
in the module is the single source and hatchling reads it at build time. The release job additionally
refuses to publish when the pushed tag does not equal `bajutsu.__version__`, so a tag can never
disagree with the artifact it produced.

### `bajutsu --version`

There is no such flag. A Typer callback on the root application prints the version and, when a `.git`
directory is present, the same short commit the `serve` version endpoint already reads. It is one
small unit, and the first thing anyone types after an install.

### The release workflow

A new workflow triggered on a `v*` tag push:

1. `make check` — never publish red, the same contract every branch is held to.
2. The tag-versus-`__version__` guard.
3. `uv build`, producing an sdist and a `py3-none-any` wheel.
4. **Trusted publishing over OpenID Connect**, not a long-lived token in repository secrets. Given
   this repository's secret-scanning posture, a publish token would be the highest-value secret in
   it; OpenID Connect removes it entirely.
5. A GitHub Release carrying the artifacts, with notes generated from the merged pull-request titles
   in the range. No committed changelog file, consistent with this repository's preference for
   derived indexes over committed ones that go stale.
6. **Post-publish verification in clean virtual environments**, which is where the workflow earns its
   keep:
   - `pip install bajutsu`, then assert `anthropic` is **not** importable. That proves
     [BE-0111](../BE-0111-ai-sdk-optional-dependency/BE-0111-ai-sdk-optional-dependency.md)'s
     AI-free base-install guarantee against the published artifact, rather than against a development
     sync that has the `ai` extra installed.
   - `pip install` each of the four self-referential extras, resolvable for the first time.
   - `bajutsu --version`, `bajutsu schema`, and `bajutsu lint` on a fixture — the device-free surface,
     exercised from an installed wheel.

A dry-run job runs steps 1 to 3 plus a metadata check on any pull request touching `pyproject.toml`
or the workflow, so packaging breakage surfaces on a branch rather than on a tag.

### The XCUITest runner is the hard part

[BE-0292](../BE-0292-xcuitest-bundled-runner/BE-0292-xcuitest-bundled-runner.md) force-includes the
built runner into the wheel, but that directory is produced by a make target needing **Xcode on
macOS**, and its build metadata records the Xcode version, the software development kit (SDK)
version, and a source hash. A Linux-built wheel would ship without it. A macOS-built wheel would ship
a Simulator-only runner whose Xcode compatibility **a wheel platform tag cannot express**, so `pip`
would resolve and install a runner the user's Xcode cannot run, and the failure would surface as a
confusing runtime error rather than a resolution failure.

The decision: **the base wheel stays pure-Python and carries no runner.** It fully serves web and
Android, and serves iOS whenever the target names its own runner or build settings — the two knobs
BE-0292 made optional without removing. The runner ships as a **companion distribution**, a
macOS-platform wheel carrying the runner alone, pulled by a new `ios` extra so a Mac user types
`pip install 'bajutsu[ios]'`. Because the platform tag still cannot encode the Xcode version,
`doctor` gains a check comparing the installed runner's build metadata against the local
`xcodebuild -version` and says so in plain words.

### The Android UI Automator server

Already optional and already degrading: when the resident server is not built, the Android
environment reads the tree with `uiautomator dump` instead
(`bajutsu/common/platform_lifecycle/environments/android.py:174`) — slower per read, but a complete
accessibility tree. A pip install therefore works for Android today at reduced speed rather than
reduced reach.
The server's build outputs are architecture-independent data, so including them keeps the wheel
`py3-none-any`, with a Gradle step in the release workflow. This is its own unit, so it can be
deferred to a second release without blocking the first.

### Documentation that must stop over-promising, and metadata that must start

[README](../../README.md) and the [getting-started guide](../../docs/getting-started/index.md), with
their Japanese mirrors, gain the honest install matrix: base install for web and Android, the browser
install for web as today, and the `ios` extra plus the Xcode-version note for iOS. The Japanese
[README](../../README.ja.md) carries no install instruction at all today, so it gains one here for
the first time.
[ai-boundary](../../docs/ai-boundary.md)'s base-install claim gains the release job's verification as
its evidence.

Two packaging-metadata repairs land with them. `readme = "DESIGN.md"` (`:5`) points a package index's
project page at a 56 KB Japanese design document; it should be the README, whose relative links must
become absolute documentation-site links, since a package index renders relative links as broken and
that page is the first thing an evaluator sees. And `[project.urls]` is absent entirely: homepage,
documentation, repository, issues.

### Work breakdown (MECE)

1. **Version single-sourcing.** `dynamic = ["version"]`, `[tool.hatch.version]`, `0.1.0` in
   `bajutsu/__init__.py`, and the tag-versus-`__version__` guard.
2. **`bajutsu --version`.** The root callback and its [cli](../../docs/cli.md) entry.
3. **Release workflow.** Tag trigger, `make check`, `uv build`, trusted publishing, generated notes,
   and the pull-request dry-run job.
4. **Post-publish verification.** Clean-environment checks for the AI-free base install and each
   self-referential extra.
5. **Packaging metadata.** The readme pointed at the README with absolute links, `[project.urls]`,
   and classifiers.
6. **The XCUITest runner path.** The companion distribution, the `ios` extra, and the `doctor`
   Xcode-compatibility check.
7. **The UI Automator server.** Package data plus the Gradle step in the release workflow.
8. **Documentation.** The install matrix in both READMEs and the getting-started guide, and
   `ai-boundary`'s evidence line.

### Prime directives preserved

- **No LLM on the run path.** Nothing here touches the runner or a verdict; it is packaging and
  release engineering.
- **Determinism.** The release is gated by the same `make check` every branch runs, and the
  post-publish checks verify the artifact rather than the working tree.
- **App-agnostic.** The install matrix distinguishes platforms by backend, not by application, and
  the `ios` extra carries a toolchain artifact rather than any per-app knowledge.

## Alternatives considered

- **Publish a macOS wheel with the XCUITest runner inside.** Rejected: a wheel's platform tag encodes
  the operating system and architecture, not the Xcode or SDK version the runner was built against —
  the two facts the runner's build metadata records precisely because they matter. `pip` would
  resolve and install a runner that cannot run, and the user would meet it as a runtime failure
  rather than a dependency error. A companion distribution plus a `doctor` compatibility check keeps
  the mismatch visible.
- **Calendar versioning.** Genuinely attractive for a project shipping many roadmap items quickly
  with no external users. Rejected: it communicates recency and communicates nothing about
  compatibility, and this repository's culture is to make a compatibility promise explicit — `schema:`
  is exactly that. With Semantic Versioning the two promises are separable and both stated; with
  calendar versioning neither is.
- **Publish only an sdist and let users build.** Rejected: the sdist would need the build backend
  plus, on macOS, the Xcode toolchain to be useful for iOS, which is the clone-and-toolchain cost
  this item exists to remove.
- **Read the version from installed distribution metadata**, making `pyproject.toml` authoritative.
  Rejected: it turns `__version__` into a runtime lookup that raises on any checkout not installed as
  a distribution, and that attribute is read on the `serve` request path (BE-0272).

## Progress

> Keep this current as work proceeds. The checklist mirrors the MECE work breakdown in
> *Detailed design* (one box per unit of work); the log records what changed and when
> (oldest first), linking the PRs.

- [ ] Version single-sourcing and the tag guard.
- [ ] `bajutsu --version` and its CLI reference entry.
- [ ] The release workflow, with trusted publishing and the pull-request dry run.
- [ ] Post-publish verification in clean environments.
- [ ] Packaging metadata — readme, URLs, classifiers.
- [ ] The XCUITest runner companion distribution, the `ios` extra, and the `doctor` check.
- [ ] The UI Automator server as package data.
- [ ] Documentation — the install matrix in both languages.

Open questions to settle while building:

- Whether the distribution name is available on the package index. Register it before anything else;
  the whole item depends on it.
- Whether the first release includes the companion runner distribution, or an interim form that
  attaches the runner to a GitHub Release with a documented download step.
- A yanking and hotfix policy, and whether pre-1.0 releases go to a test index first as a matter of
  course.
- Whether the documentation site should be versioned alongside releases, or stay single-version. Out
  of scope here, but decided by this item's cadence.

## References

- [BE-0292 — Bundle the XCUITest runner so testRunner is optional](../BE-0292-xcuitest-bundled-runner/BE-0292-xcuitest-bundled-runner.md)
  — the force-include this item must place somewhere a wheel can honestly carry.
- [BE-0272 — Show bajutsu's running commit/version in the serve Web UI header](../BE-0272-serve-version-badge/BE-0272-serve-version-badge.md)
  and [BE-0277 — Embed the commit hash into self-hosted Docker images](../BE-0277-docker-build-commit-badge/BE-0277-docker-build-commit-badge.md)
  — the two shipped features degraded by the absence of a release pipeline.
- [BE-0111 — Make the AI SDK an optional extra](../BE-0111-ai-sdk-optional-dependency/BE-0111-ai-sdk-optional-dependency.md)
  — the guarantee the post-publish check proves against the artifact.
- [BE-0119 — Version the scenario schema for cross-version reads](../BE-0119-scenario-schema-versioning/BE-0119-scenario-schema-versioning.md)
  — the compatibility promise the package version deliberately does not carry.
- [BE-0164 — Config-aware environment installer](../BE-0164-config-aware-environment-installer/BE-0164-config-aware-environment-installer.md)
  and [BE-0173 — Slim Linux web-worker container image](../BE-0173-slim-web-worker-image/BE-0173-slim-web-worker-image.md)
  — what a fresh install still needs beyond the wheel, and the worker's runtime closure extras.
- `pyproject.toml` (`:3` version, `:5` readme, `:31`/`:41`/`:45`/`:70` the self-referential extras),
  `bajutsu/__init__.py:3`, `README.md:167`, `docs/getting-started/index.md:49`,
  `bajutsu/common/platform_lifecycle/environments/android.py:174` (the `uiautomator dump` fallback).
