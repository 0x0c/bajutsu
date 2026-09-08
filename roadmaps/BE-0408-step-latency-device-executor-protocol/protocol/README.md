# The device-side step-execution protocol (BE-0408)

[`device-executor.openapi.yaml`](device-executor.openapi.yaml) is a draft OpenAPI 3.1 document —
not a live contract either runner implements yet. It is the single source of truth both
[BE-0409](../../BE-0409-step-latency-ios-device-executor/BE-0409-step-latency-ios-device-executor.md)
(iOS) and
[BE-0410](../../BE-0410-step-latency-android-device-executor/BE-0410-step-latency-android-device-executor.md)
(Android) implement against, so the new endpoints carry identical JSON schemas on both platforms
rather than diverging the way the two platforms' *existing* wire formats already have (iOS: an
established OpenAPI/JSON contract; Android: query parameters and XML, with no JSON at all today).
This document explains the design decisions the schema file states only tersely.

## Why this document is not the live contract

`BajutsuKit/Sources/BajutsuRunner/openapi.yaml` feeds Swift OpenAPI Generator's build plugin, which
regenerates `APIProtocol` — the interface `APIHandler.swift` implements — at every build
([BE-0381](../../BE-0381-runner-openapi-contract/BE-0381-runner-openapi-contract.md)). Adding a
path directly to that file would grow `APIProtocol` with a method `APIHandler` does not yet
implement, breaking the iOS build immediately — in an item ([BE-0408](../BE-0408-step-latency-device-executor-protocol.md))
that touches no Swift or Kotlin code. BE-0409 merges this document's paths into that live file, in
the same commit that adds the matching `APIHandler` conformance. BE-0410 implements the same
schemas over the Android resident server, by hand today (see *Android transport* below).

## What stays out of scope

iOS's existing eighteen paths and Android's `/act` / `/source` / `/clock` are shipped, measured
behavior ([BE-0407](../../BE-0407-step-latency-driver-internal-tuning/BE-0407-step-latency-driver-internal-tuning.md))
and are not redesigned here. A single already-optimized call does not get faster by changing its
wire format alone — `/tap` and `/act` are already one round trip each. Where stage 4 bundles an
actuation kind that already has a standalone endpoint, it reuses that endpoint's existing request
shape (see *Stage 4* below) rather than inventing a second one — that reuse, not a rewrite of the
standalone endpoints, is how this document brings the existing actuation surface into the
round-trip win.

## Stage 1 — `POST /wait`

Covers `Wait.for_` (`for`), `Wait.until: Gone` (`until: gone`), and `Wait.until: "screenChanged"`
(`until: screenChanged`) — three of the four wait kinds `_wait`
(`bajutsu/common/orchestrator/waits/_functions.py`) evaluates by polling the device tree every 50
milliseconds today. `until: settled` folds into the same endpoint as a fourth `mode` value (see
*Stage 2* below). `until: request` is not covered: it polls the observed network, never the device
tree, so moving it here would not remove a device round trip.

### The applicability boundary

A `wait` step whose scenario has `alert_guard` configured, or that declares `interrupts` handlers,
stays on the legacy host-polled path — `POST /wait` is used only when neither applies. Both
mechanisms can run arbitrary host-orchestrated recovery mid-wait: `_AlertGuardGate.observe()` can
tap a system-alert button it recognizes from the visible tree (or, on iOS, query SpringBoard
natively) and record the dismissal for the report; `on_interrupt_poll` can run a scenario's full
`interrupts` recovery `steps`, including further actuation or network calls. Neither belongs
inside a device-side condition evaluator, and neither is part of this item's selector-semantics
scope. A scenario using either mechanism keeps paying the 50-millisecond poll for the affected
wait steps; every other wait moves to `POST /wait`.

### Cancellation and the `pollBudgetMs` design

The most consequential correction in this document's design, found while pressure-testing an
earlier draft: closing the HTTP connection to cancel an in-flight device-side wait does not work
today, on either side. Neither runner's connection handler reads from its own socket while a
long-running call is in progress — `HTTPServer.swift`'s `handleConnection` and
`ResidentServerTest.kt`'s `handle()` loop both run the handler to completion before touching the
socket again — so detecting a closed peer mid-call is new work neither implementation does
anywhere today. The bigger gap sits on the host: `cancelled()`
([BE-0370](../../BE-0370-graceful-run-cancel/BE-0370-graceful-run-cancel.md)) is checked *between*
polls, because the
host itself owns the poll loop today and is never blocked inside one long call. Moving the whole
loop onto the device would need a background thread able to force-close a blocked
`http.client.HTTPConnection` from outside — a capability this driver stack has never needed and
does not have.

Building that capability is out of this item's scope (it defines a protocol; it writes no driver
code). So `WaitRequest` carries a required `pollBudgetMs`: the upper bound on one call, distinct
from `timeoutMs`, the wait's whole deadline. The host repeats `POST /wait` in a loop bounded by
`pollBudgetMs` until either a call reports `ok` or `timeoutMs` passes — the same loop shape `_wait`
already has, just with an interval measured in roughly a second rather than fifty milliseconds. A
`pollBudgetMs` in the 1000–2000 millisecond range keeps cancellation exactly as responsive as it is
today (checked between calls, no new concurrency primitive) and still collapses round trips by
roughly twenty to forty times over the 50-millisecond baseline — short of the fully collapsed
single round trip this item's Motivation names as the eventual target, but achievable without new
cross-thread cancellation infrastructure. A future revision may add a true single-call mode once
that infrastructure exists elsewhere; this document does not assume it will.

### The reply shape

`WaitReply.elements` carries the last tree this call queried, for every mode — the host reuses it
as the step's `after` evidence
([BE-0259](../../BE-0259-assert-query-snapshot-reuse/BE-0259-assert-query-snapshot-reuse.md))
instead of a second `/elements` round trip. `WaitReply.trace` mirrors `WaitTrace`
(`bajutsu/common/orchestrator/waits/wait_trace.py`) and is present only when `mode: for` times out
— the same scoping `WaitTrace` has today, where only the `for` branch ever populates it.

**`trace` is a per-call fragment, and the host must accumulate it — this document does not do
that accumulation for you.** `WaitTrace.polls` and `firstNonemptyMs` are scoped to the one bounded
`pollBudgetMs` call that produced them, not to the wait step as a whole. Under the `pollBudgetMs`
loop, a 30-second `for` wait issues roughly twenty calls, and every one of them except the last
reports `status: timeout` — that is now the *normal* shape of an in-progress wait, not only its
final failure, unlike today's single-call `_wait` loop where a `timeout` status only ever means the
whole step failed. A host implementing this loop must sum `polls` across every call in the
sequence, and must offset `firstNonemptyMs` by the cumulative elapsed time of the calls before the
one that reports it, before writing either into the step's `WaitTrace` evidence — reporting one
call's raw `polls: 14` for what was actually a 30-second wait would understate the diagnostic by
the same factor `pollBudgetMs` collapses the round trips by. BE-0409 and BE-0410 must implement
this same aggregation, not invent their own independently.

## Stage 2 — `until: settled`

Folded into `POST /wait` as a fourth `mode` value rather than a separate endpoint: `settled`, like
`screenChanged`, needs no `selector` field, and the host-side loop shape (bounded calls repeated
under `timeoutMs`) is identical. What differs is internal to each platform, not part of the wire
contract: BE-0409's own design already plans to extend the BE-0310 screen-transition signal to
reach the iOS runner directly, and BE-0410's own design already plans to evaluate settle from
Android's accessibility-event stream rather than the two-dump comparison `/act` uses today. Both
report back through the same `status: ok | timeout` this document already defines for every other
mode.

## Stage 3 — `POST /assert`

Covers every screen-closed assertion kind — `exists`, `value`, `label`, `count`, `enabled`,
`disabled`, `selected` — the same seven that already resolve through `find_all` or `resolve_unique`
on the host today (`bajutsu/common/assertions/evaluate/_functions.py`). `AssertRequest.kind` picks
which of the source Pydantic models' fields apply, mirroring `Exists`, `TextMatch`, and
`CountMatch` (`bajutsu/common/scenario/models/assertions/`) field-for-field, so a device-side
implementation's parsing logic has a one-to-one source to check itself against. The seven
remaining assertion kinds — `request`, `event`, `requestSequence`, `responseSchema`, `visual`,
`clipboard`, `golden` — all stay host-side. Most never resolve a selector against the element tree
at all (they read captured network exchanges, or compare against a stored file). `visual` is the
exception: `VisualMatch.element` and its `exclude` list's `SelectorRegion` entries do resolve a
selector (`bajutsu/common/scenario/models/assertions/visual_match.py`,
`selector_region.py`) — what keeps it host-side is that its verdict is a pixel comparison against
a stored baseline image, which is not a machine-checkable judgment this protocol's selector
contract has any reason to move, not an absence of selector resolution.

## Stage 4 — `POST /scenario`

Bundles `tap`, `type`, `wait`, and `assert` steps into one call — the point this item's own
Motivation names as the target: a scenario segment costs at most one round trip once every
individual step kind resolves on the device. `wait` and `assert` steps reuse this document's own
`WaitRequest` / `AssertRequest` payloads unchanged. `type` reuses the existing standalone
`TypeRequest` shape (`text` only) — a bundled `type` still targets whatever element is currently
focused, the same semantic the standalone `/type` endpoint already has, so no redesign is needed.

### What `pollBudgetMs` means for a bundled `wait` step

Reusing `WaitRequest` unchanged means a bundled `wait` step's `payload` still carries a required
`pollBudgetMs` — the schema does not distinguish standalone from bundled use. Its *meaning*
changes, though. Stage 1's `pollBudgetMs` exists so the host can re-issue `POST /wait` in a bounded
loop (see *Cancellation and the `pollBudgetMs` design* above); inside a `POST /scenario` call there
is no per-step re-issue to bound — the "one call" already in flight is the whole bundle, not the
individual step. A device that honored `pollBudgetMs` *inside* a bundle by returning a
`status: timeout` for that one step and stopping there would need the host to reconstruct which
steps remain and re-send them, a shape this document defines no schema for. A device that instead
ignores `pollBudgetMs` for a bundled `wait` — blocking that one step out to its own `timeoutMs`,
inside the still-open bundle call — delivers the one-round-trip-per-segment result this stage
exists for. This document specifies the second reading: **inside a `POST /scenario` bundle,
`pollBudgetMs` is present (the schema requires it) but not honored; a bundled `wait` step blocks
until its condition holds or its own `timeoutMs` elapses, whichever comes first, within the single
bundle call.** BE-0409 and BE-0410 must implement this same reading, not invent their own —
inconsistent readings would make a bundle's actual latency behavior diverge silently between
platforms, exactly the kind of drift this document exists to prevent.

`tap` is the one kind that does *not* reuse its existing standalone shape. iOS's `TapRequest` takes
a `handle` (or a raw `point`); Android's `/act` takes already-resolved identity fields
(`rid`/`desc`/`text`/`cls`/`index`/`count`) the host computed via a prior `resolve_unique` call.
Both assume something already resolved *before* the call — exactly the round trip this whole item
exists to remove. `ScenarioTapRequest` instead carries a `selector`, resolved fresh on the device
at the moment the tap fires, the same way `WaitRequest.selector` and `AssertRequest.selector`
already do. This also sidesteps a real risk a handle-based bundled tap would carry: a handle minted
early in a long bundle could go stale by the time a later step in the same bundle acts on it, while
a fresh `selector` resolution never can.

### Why `swipe` and `scroll` are named but not specified

Both are geometry-driven today, not selector-driven — a `swipe` is a raw two-point drag with no
selector at all, and a `scroll` step's most valuable device-native form (resolve a target, decide
whether it is already on screen, and drag exactly far enough to reveal it) needs the
`scroll_to_target` viewport and step-fraction math that lives host-side today
(`bajutsu/common/orchestrator/actions/handlers/scroll.py`, reused directly by
`tests/driver_conformance.py`'s scroll invariants). Porting that math to Swift and Kotlin is real,
separate design work this document does not attempt — bundling `swipe` and `scroll` is a stated,
deliberate gap for a later revision of this document, not an oversight.

### Two questions left for the first implementation

- **Mid-bundle failure handling.** Whether `ScenarioReply.results` may be shorter than
  `ScenarioRequest.steps` — stopping at the first failing step, matching how a scenario's own step
  loop (`bajutsu/common/orchestrator/loop/`) already stops at the first failing step — or always
  runs every step regardless, is not decided here. Whichever BE-0409 or BE-0410 implements first
  should match the host's own step-loop failure semantics, and this document should be revised
  (with the box below checked and a dated entry added) once that choice is made, so the second
  platform inherits the same answer instead of independently rediscovering it.
- **Evidence retrieval.** `ScenarioStepResult.evidenceToken` is an opaque placeholder for a
  screenshot-and-tree fetch that stays off the critical path, per BE-0409's own stated design (its
  fourth executor responsibility: "return the screenshot and the element tree asynchronously,
  alongside the step's result"). The retrieval endpoint itself — a `GET`, a follow-up `POST`, or
  something else — is left to whichever platform item defines it first.

## Android transport

The Android resident server (`BajutsuAndroidUIAutomatorServer/server/src/androidTest/java/dev/bajutsu/android/server/ResidentServerTest.kt`)
carries zero JSON and zero HTTP library today, by an explicit, recorded design choice
(`server/build.gradle.kts`: "no HTTP or JSON library, so the instrumentation APK stays small and
dependency-light"). This document's new endpoints need JSON bodies, so implementing them changes
that server in two ways BE-0410 should plan for.

**Request parsing needs a real fix, not a drop-in.** `readRequestTarget` (lines 172–196) already
reads a `Content-Length` header and drains that many bytes today, and the loop's own byte
accounting is already correct — each iteration measures what it actually consumed with
`String(buffer, 0, read).toByteArray(StandardCharsets.UTF_8).size`. The bug is in what it *asks*
for: `reader.read(buffer, 0, minOf(left, buffer.size))` requests up to `left` **characters** off a
`BufferedReader`, while `left` counts **bytes** remaining. Every request body sent today is empty,
so this mismatch has never mattered in practice. A `POST /wait` body carrying non-ASCII text
(`label` / `labelMatches` can carry Japanese, and this is a bilingual codebase) changes that: a
multibyte character costs more bytes than the one character the read request assumes, so the call
can read characters belonging to the *next* pipelined request on the same keep-alive connection —
desynchronizing the stream rather than merely mis-draining an unused body. `HTTPServer.swift`
avoids exactly this by staying byte-oriented throughout — decoding to UTF-8 only for header lines,
treating the body as raw bytes — and Android's new body-reading path needs the same discipline:
read exactly `Content-Length` raw bytes from the underlying `InputStream`, then decode those bytes
to UTF-8 for `org.json`. Response writing needs no such fix — `respond()` (lines 655–675) already
accepts an arbitrary `contentType` and a raw `body: ByteArray`, so serving `application/json` is a
one-line change.

**Recommendation: `org.json` for now, `openapi-generator`'s Kotlin models for BE-0410 to evaluate.**
`org.json` (`JSONObject` / `JSONArray`) ships in the Android platform SDK — no new Gradle
dependency — and is already this repository's own precedent for JSON on Android
(`BajutsuAndroid/src/main/java/dev/bajutsu/android/BajutsuNet.kt`). It keeps the resident server's
dependency-light instrumentation APK unchanged for whichever endpoints BE-0410 implements first by
hand. But hand-written field access (`json.optString("mode")` and so on) risks the exact kind of
silent schema drift a strict, machine-checked contract exists to prevent: a dropped or renamed
field degrades to a wrong runtime value instead of a compile error. Kotlin OpenAPI code generation
has zero precedent anywhere in this repository today (no `org.openapi.generator` Gradle plugin, no
Kotlin client checked in), so this document recommends — without mandating, since it writes no
Kotlin code itself — that BE-0410 evaluate `openapi-generator`'s Kotlin generator in its
models-only mode (generating `@Serializable` data classes from this document's schemas, paired
with `kotlinx.serialization`, and leaving the socket-level dispatch hand-written) before committing
to fully hand-rolled parsing. This mirrors the split BE-0381 already made for iOS: `Types.swift`
generated, `APIHandler.swift` hand-written. Adopting it costs a new Gradle dependency (the
generator plugin, `kotlinx.serialization`'s runtime, and its Kotlin compiler plugin) — a deliberate
departure from today's zero-JSON design that BE-0410 should record explicitly if it takes this
path, the same way BE-0381's own Unit 2 ran a short proof-of-concept (Hummingbird vs. FlyingFox)
before committing to a transport. A `frame: [number, number, number, number]` fixed-length array is
the one schema shape in this document worth checking early in such a proof-of-concept: most Kotlin
generators turn it into a `List<Double>` with no compile-time length guarantee, which is a known
limitation to accept, not a blocker.

## Machine-checked conformance

`tests/fixtures/be0408/protocol/` holds wire-structure fixtures — one `{"request": ..., "response":
...}` pair per file, several per operation. Coverage per operation: `wait`'s `ok` and `timeout`
outcomes, `assert`'s `ok: true` and `ok: false` outcomes, and `scenario`'s all-succeeding and
one-step-failing bundles. The `ErrorReply` / 400 `BadRequest` shape this document defines carries
no fixture: every fixture's `response` validates against the operation's own reply schema, and the
format has no way to express a malformed request's rejected shape yet.
`tests/test_be0408_protocol_fixtures.py` loads this document with `pyyaml` (an existing base
dependency) and validates each fixture's request and response against the matching
`components/schemas` entry with `jsonschema` (the `schema` extra, already in the gate's `dev`
dependency group) — the same `jsonschema.validate` idiom
`bajutsu/common/assertions/schema.py` already uses for the `responseSchema` assertion kind. This is
a *structural* check only: does a given JSON payload have the shape this document declares. It is
deliberately separate from the *semantic* fixtures at `tests/fixtures/be0408/selector_resolution.json`
and `android_derived_label.json`, which check whether a selector resolves to the *same element* a
device-side port would need to pick — a JSON Schema check cannot express that question, only a
replay against the real `find_all` / `resolve_unique` implementation can (see
`tests/test_selector_fixtures.py`). Together the two suites are this item's answer to "a strict
spec": every future PR that drifts from either the wire shapes or the resolution semantics fails
the fast Linux gate, no device needed, before it ever reaches a platform implementation.

## Revision history

- **0.1.0** (this revision) — Initial draft: stages 1–4, the `pollBudgetMs` cancellation design,
  and the Android transport recommendation.
