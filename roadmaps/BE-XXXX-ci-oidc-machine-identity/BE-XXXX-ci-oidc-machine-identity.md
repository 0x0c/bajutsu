**English** · [日本語](BE-XXXX-ci-oidc-machine-identity-ja.md)

# BE-XXXX — Authenticate a CI job to serve with a GitHub Actions OIDC token

<!-- BE-METADATA -->
| Field | Value |
|---|---|
| Proposal | [BE-XXXX](BE-XXXX-ci-oidc-machine-identity.md) |
| Author | [@paihu](https://github.com/paihu) |
| Status | **Proposal** |
| Tracking issue | [Search](https://github.com/bajutsu-e2e/bajutsu/issues?q=is%3Aissue+label%3Aroadmap-tracking+in%3Atitle+"BE-XXXX") |
| Topic | Hosting the web UI |
| Related | [BE-0313](../BE-0313-github-org-team-rbac/BE-0313-github-org-team-rbac.md), [BE-0051](../BE-0051-serve-hardening-for-hosting/BE-0051-serve-hardening-for-hosting.md), [BE-0015](../BE-0015-web-ui-public-hosting/BE-0015-web-ui-public-hosting.md) |
<!-- /BE-METADATA -->

## Introduction

A hosted `bajutsu serve` authenticates two kinds of caller today. A human signs in through GitHub
OAuth (Open Authorization) and gets an identity, which the role gate then checks per endpoint
([BE-0313](../BE-0313-github-org-team-rbac/BE-0313-github-org-team-rbac.md)). A worker presents the
shared token ([BE-0051](../BE-0051-serve-hardening-for-hosting/BE-0051-serve-hardening-for-hosting.md))
and gets no identity at all.

A continuous-integration (CI) job is neither. It cannot complete a browser sign-in, and on a
deployment with OAuth configured the shared token no longer reaches any endpoint outside worker
traffic. This item gives such a job an identity of its own: it presents the OpenID Connect (OIDC)
token GitHub Actions issues to a workflow once, to a dedicated exchange endpoint. serve verifies
that token there and mints a short-lived machine session in its place, and the repository named in
the token's claims decides which org that session acts as. Access is scoped to what a machine
needs — never to a human role.

## Motivation

BE-0313 replaced serve's login allowlist with GitHub's own organization and Team membership, and
narrowed the shared token to worker traffic in the same change. That was the right move for people:
an identity the role gate can check beats a secret that grants everything. It left machines with no
replacement, and `docs/self-hosting.md` records the consequence plainly — a deployment that scripted
non-worker endpoints with the token loses that path once OAuth is on.

The hole is visible in the request gate. `_gate` in `bajutsu/serve/handler.py` authenticates a
request, then splits on whether it carries an identity. An OAuth session has one, so
`forbidden_for_role` checks it. A bearer-token request has none, and its own comment says what
follows: it "stays full-access (the operator credential)". Serve therefore knows exactly two
shapes, and a CI job fits neither.

| Caller | Credential | Identity | Access |
|---|---|---|---|
| Human | GitHub OAuth session | GitHub login | role-gated: viewer / editor / admin |
| Worker | shared token | none | full, on worker routes |
| CI job | *(none available)* | — | — |

Handing CI the shared token where it still works does not close that hole either, for two reasons
beyond the OAuth case. A shared secret cannot say *which* pipeline acted, so an audit trail records
"the token" and stops there. And it is identity-less, so it arrives with full access — a credential
in every pipeline that can rebind an org's configuration or read a config body with embedded
secrets.

Concretely, five endpoints a CI pipeline has reason to call are closed to it. `POST
/api/artifacts/binary` and `GET /api/artifacts/exists` require the admin role. `POST /api/run`
requires editor. The job-scoped binary artifact override proposal, a sibling of this item, wants
exactly that sequence: upload a build, then dispatch a run naming it. It can only assume the
credential a token-authenticated deployment already trusts, and on an OAuth deployment it has
nothing to assume. A pipeline publishing a configuration or a scenario tree alongside its build
needs two more admin-tier routes, `POST /api/artifacts/config` and `POST /api/artifacts/scenarios`.
The allowlist below therefore covers all three artifact kinds, not the binary alone.

**Verifiable outcome.** A GitHub Actions workflow with `permissions: id-token: write` and **no
repository secret** dispatches a run against an OAuth-configured deployment, and the run lands in
the org the workflow's repository belongs to. A workflow in a repository the org does not list is
refused with 403. And the run's audit record names that repository, rather than recording only that
a token was presented.

## Detailed design

The work is mutually exclusive and collectively exhaustive (MECE) across four units: verifying the
token, mapping its claims to an org, deciding what a machine may do, and the tests plus
documentation.

### Unit 1 — Exchange the token once for a machine session

The pipeline this item targets calls three endpoints in sequence: `GET /api/artifacts/exists`, then
`POST /api/artifacts/binary`, then `POST /api/run`. A scheme that verified an OIDC token on every
request, and refused a `jti` it had already seen, would refuse that sequence at its second call —
the token's `jti` is already spent by the first. A per-request scheme with a single-use replay
defense cannot serve this pipeline. So serve verifies the token exactly once, at a dedicated
exchange endpoint, `POST /api/oidc/exchange`, and mints a short-lived **machine session** that every
later call in the sequence presents instead. Every check below still runs in full — just once, at
the exchange, rather than on every request.

GitHub Actions issues a signed JSON Web Token (JWT) to any workflow job that declares
`permissions: id-token: write`. The job requests it from `$ACTIONS_ID_TOKEN_REQUEST_URL` with
`$ACTIONS_ID_TOKEN_REQUEST_TOKEN`, both available once the job declares that permission. No GitHub App, OAuth
app, or identity-provider registration is involved on GitHub's side. The job sends the result to the
exchange endpoint as a bearer token, and serve verifies the signature there before trusting any
claim:

- **Issuer.** `iss` must equal the configured issuer, `https://token.actions.githubusercontent.com`
  for GitHub-hosted Actions.
- **Signature.** RS256 against the issuer's JSON Web Key Set (JWKS), discovered from
  `/.well-known/openid-configuration` and cached with a time-to-live so an exchange does not fetch
  keys. The verifier passes an explicit algorithms allowlist of RS256. It refuses any token whose
  header names a different algorithm. The token itself never picks the algorithm, which is what the
  classic JWT forgeries turn on: `alg: none`, or HS256 checked against the RSA public key bytes. The
  issuer's discovery document advertises RS256 alone, so this check costs nothing. A JWKS entry
  counts as a match when its key type is RSA and its advertised algorithm agrees. A key id (`kid`)
  missing from the cache triggers a refresh, capped by a refresh-interval floor (or a negative cache
  of missing key ids): without that cap, anyone could force one outbound fetch per call by sending a
  random `kid`, before authenticating. Only the exchange endpoint carries that exposure now rather
  than every request, and the cap still matters there, since the endpoint takes no prior serve
  credential (Unit 3). The fetch carries a timeout, since the gate runs synchronously in the stdlib
  backend. A key set that cannot be fetched, with an expired cache, refuses the exchange instead of
  trusting a stale one — a rotated-out key must not stay acceptable. A signature that still fails to
  verify fails closed too.
- **Audience.** `aud` must equal a value the **deployment** configures. This is the one check an
  operator must not skip. The workflow chooses its own audience — `core.getIDToken(audience)` takes
  it as an argument — so a deployment that accepts any `aud` accepts a token minted for an unrelated
  service. A deployment with no expected `aud` configured disables the OIDC caller shape entirely. An
  exchange request presenting an OIDC token gets refused outright, never falling back to accepting
  any audience. Fail closed, not operator discipline.
- **Lifetime.** `exp` and `nbf`, with a small skew allowance, matching the 60-second backdating
  `bajutsu/common/github/app.py` already applies when it signs an App JWT.
- **Replay.** GitHub documents no numeric token lifetime, so a captured token is replayable for its
  whole window. Serve spends each token's `jti` (documented as a unique identifier) in a replay cache
  bounded by that token's `exp`, and refuses a token past a serve-side age ceiling independent of
  `exp`. The cache lives in the shared system of record — the `Repository` seam, alongside the
  encrypted operator secret store — because `docs/self-hosting.md` documents the hosted control plane
  as multiple replicas sharing that store. A per-process cache would fall to a replay against a
  second replica, leaving the age ceiling as the only real bound. It costs one write per job, since
  an exchange happens once per job rather than once per call.

Verification uses [`joserfc`](https://jose.authlib.org/), a maintained JOSE (JavaScript Object
Signing and Encryption) implementation. Unit 1 declares it directly in the `oauth` extra: `authlib`
began depending on it only in 1.7.0, so the extra's `authlib>=1.3` floor does not guarantee it, and
today's lock has it only because that lock pins 1.7.2. The verification itself — the JWKS fetch, its
cache, and the checks above — lives in its own module, imported lazily once OIDC is configured, so
`bajutsu/serve/gate.py` keeps only the machine-session policy decision (Unit 3). That split is
forced: `bajutsu/serve/__init__.py` imports `gate` unconditionally, and `joserfc` ships only with the
`oauth` extra, so a module-level import there would break `import bajutsu.serve` on every base
install. Unit 4 adds `joserfc` to `tests/serve/test_import_guard.py`'s `FORBIDDEN` set, which lists
`authlib` today but not `joserfc`.

**The session's lifetime never exceeds the token's,** capped by the presented token's own `exp`. The
exchange improves on reusing the token directly only if the credential it mints is shorter-lived
than the token would have been; a session outliving its own token would be a downgrade.

**What the exchange buys, and what it does not.** Resistance to a captured credential is roughly
unchanged: both are bearer credentials over TLS, and the honest difference is lifetime, which is why
the cap above matters. Four things do change. The session can be **revoked**, since the session
stores implement `revoke_identities` and serve cannot revoke a GitHub-issued token. JWT verification
and the JWKS fetch leave the per-request path, so that code is reachable pre-authentication on one
endpoint rather than on every request. Single-use `jti` becomes possible at all, which turns a
stolen token from a silent success into a **visible failure** — the attacker's exchange spends the
`jti`, so the legitimate job's exchange then fails loudly. And the minted session is worthless to
any other service, unlike a token whose `aud` another service might also accept. The cost is one
more endpoint, a session lifetime to get right, and a second credential in the pipeline.

**After the exchange, a machine request carries no JWT** — it is the same session lookup every human
request already takes. `authz.login()` mints a session from a validated credential through
`state.auth.issue_session()`, and that path is disabled once OAuth is configured, exactly where the
exchange is enabled instead.

### Unit 2 — Map the claims to an org, on the claims themselves

`OrgConfig` (`bajutsu/serve/orgs.py`) already declares who belongs to an org: `members`,
`githubOrgs`, `githubTeams`, `editorTeams`, and the `targets` it owns. This item adds
`allowedRepositories`, each entry an `"<owner>/<repo>"`. A verified token whose repository matches an
entry acts as that org; one that matches no org's entries is refused. The org comes from the
validated claim alone, never from a field the caller supplies — the rule `worker_lease` already
follows when it takes the org from the leased job rather than from the worker.

A repository listed by more than one org's `allowedRepositories` is a configuration error, refused
at startup. Humans resolve that ambiguity with a preferred org plus a selector; a machine has
neither. Configuration order would otherwise decide the winner without anyone choosing it. If the
conflict is ever reached at exchange time regardless, the exchange gets refused rather than resolved.

**`allowedRepositories` keeps `"<owner>/<repo>"` names — a consciously accepted trade-off, not a
passing caveat.** `repository` is a *mutable* name. Name recycling is precisely why GitHub
introduced immutable subjects: a listed repository that is deleted, renamed, or transferred frees
its name. Whoever claims that name next can mint tokens whose `repository` claim matches the listed
entry. This item keeps the named form, and with it an operator duty: update or remove an entry the
moment its repository is renamed, transferred, or deleted. The entry admits the name, not the
repository.

**Match the discrete claims, never a parse of `sub`.** The token carries `repository` and
`repository_owner`, plus `repository_id` and `repository_owner_id`. Authorization compares those by
exact equality. Two facts make reading `sub` the wrong choice:

- **The `sub` format has already changed for new repositories.** A repository created after 15 July
  2026 gets an immutable subject that embeds numeric ids:
  `repo:octo-org@123456/octo-repo@456789:ref:refs/heads/main`. GitHub also moves renames and
  transfers after that date to the immutable format. A listed repository can change format with
  nobody opting in — one more reason the recycling-risk entry above needs an operator watching it.
  Older repositories keep the previous shape unless they opt in. Immutable subjects are not
  available on GitHub Enterprise Server. A deployment parsing `sub` would have to handle every shape
  and would end up mis-parsing one.
- **`sub` is customizable.** A repository can redefine which claims compose the subject through an
  `include_claim_keys` array. An organization can provide only a template, one that leaves a
  repository already using OIDC unaffected unless that repository opts in. Authority sits with the
  repository, not the organization, so what `sub` contains is not serve's to assume.

Exact equality also rules out a prefix match, which is the classic failure here: `repo:acme/app`
prefix-matches `repo:acme/app-evil`, so a substring test would admit a repository the operator never
listed.

**The repository is not the whole trust boundary.** Anyone who can merge a workflow change to a
listed repository can mint a token from it. So `allowedRepositories` alone means "whoever can write
that repository's workflows may dispatch as this org". A deployment needing a tighter bound narrows
further on claims the token already carries: `environment` (a GitHub Environment can require
reviewers before a job runs), `ref`, or `job_workflow_ref`. These narrowings belong in config, not a
comment — "any branch of this repository" versus "this environment alone" is a real choice an
operator makes. `environment` is a *conditional* claim: GitHub emits it when the job
references an environment. A configured `environment` bound must therefore refuse a token whose
`environment` claim is absent, the same as one whose value differs. Otherwise a job declaring no
environment escapes the narrowing entirely.

One hazard belongs in the documentation rather than the code. A pull request from a fork does not
receive `id-token: write` by default, but a `pull_request_target` workflow runs in the base
repository's context and can. The same hazard class shows up in a repository setting that sends
write tokens to workflows from pull requests, re-enabling `id-token: write` on plain fork pull
requests. A deployment listing a repository whose pipelines use `pull_request_target`, or that turns
on that setting, should narrow by environment — so a token can never be minted from a run an
outside contributor influenced.

### Unit 3 — A machine principal, not a human role

The machine session the exchange mints is a **third caller shape**, beside the OAuth session and the
shared token. It carries an identity, like a session, and it is not a person, so no viewer / editor /
admin rank describes it. What it may do is an explicit allowlist of endpoints:

| Allowed | Refused |
|---|---|
| `POST /api/artifacts/{config,scenarios,binary}` | `POST /api/config`, `POST /api/compose` (rebinding the org's active configuration) |
| `GET /api/artifacts/exists` | `GET /api/config/content` (a config body may embed secrets) |
| `POST /api/run`, and reading runs in its org | `POST /api/apikey`, `POST /api/claudecodetoken` (operator secrets) |
| | `/api/orgs*` (who may sign in and write) |

`POST /api/oidc/exchange` itself sits outside this allowlist: it is the entry point, so it requires
no prior serve credential — only a verifiable OIDC token. Nobody should read the table above as
gating the way in; it governs what an already-minted machine session may do, not how a token
becomes one.

Run reads are **org**-scoped, not per-actor: the read paths take an `org_id` and never filter on
`created_by`, the nullable foreign key to `users.id` that already exists on `runs`
(`bajutsu/serve/server/models/run.py`). A machine reads its org's runs, including ones it did not
start. `bajutsu/serve/jobs.py` already writes `created_by` only when the actor is a user that
exists — its own comment notes that a token / CI run has no actor. A machine-dispatched run
therefore leaves the column null for free, the second foreign key a synthetic `users` row would
otherwise need to satisfy. Per-run attribution beyond that would be its own separate change.

The allowlist is what makes this safe to hand to a pipeline. Four of the endpoints it opens are
admin today. Granting a machine the admin *rank* would come with config rebinding and secret reads
attached. Naming endpoints instead keeps the machine's reach to publishing an artifact and starting
a run — the whole of what a pipeline needs. `required_role` keeps deciding what a human needs. This
allowlist governs a machine principal and nothing else, so neither gate can widen the other.

The allowlist applies to a machine principal unconditionally, with or without a database wired.
`forbidden_for_role` returns *allowed* when `state.repository is None` ("DB-less = full access",
`bajutsu/serve/authz.py`). An allowlist conditioned on the database the same way would inherit that
fail-open.

The shared policy both backends enforce lives in `bajutsu/serve/gate.py` (BE-0253), not in `_gate`
in `handler.py` alone. It exists so the stdlib handler and the FastAPI app cannot diverge on
security posture. Its own docstring calls the prior duplication "a latent path to a
security-relevant divergence with nothing checking for it", and `bajutsu/serve/server/app.py`
mirrors `handler.py` line for line. Unit 3's machine-session allowlist lands in `gate.py`, alongside
the human role gate it already enforces, so both backends get the machine principal from one place.
Unit 1's token verification lives in its own lazily-imported module (above), reached only by the
exchange endpoint, never by `gate.py` itself. An OIDC token presented as a bearer credential is
neither the shared token nor a valid session, so it falls through `gate.is_authorized` today and
gets denied. This item adds the machine session as a third branch there, checked the same way an
OAuth session already is.

**The org travels with the machine session, not through `org_of`.** Today every `start_*` endpoint
resolves the org through `state.org_of(actor)`, which reads the actor's *persisted user row*. Two of
the endpoints the allowlist opens first do the same: `bind_artifact` and `artifact_exists`
(`bajutsu/serve/operations/upload.py`) each take `org = state.org_of(actor)`, using it for the
object-store key, the local cache path, the audit row, and the exists probe. A machine has no row,
so `org_of` would answer `default` for every one of those calls whatever `allowedRepositories` says.
That is a cross-tenant hole on a multi-org deployment, on the very routes the allowlist opens first.
Instead, every allowlisted operation reads the org from the machine session, resolved once at
exchange (Unit 1). The dispatch path is one instance of that rule, not the whole of it.

Minting a synthetic `users` row to carry that org instead brings its own cost. Such a row would
also carry a role column, so `forbidden_for_role` would start applying a human role to the machine
(an unknown user defaults to viewer, which refuses `POST /api/run`). The machine would also show up
in the roster `/api/orgs` discloses.

For the same reason, the audit record does not gain the repository as an *actor*. `actor_id` is a
nullable foreign key to `users.id` (`bajutsu/serve/server/models/audit_log.py`), and minting a
synthetic row to meet that constraint carries the cost described above. `actor_id` stays null for a machine
request; the repository goes into the audit entry's own detail payload instead. That answers "which
pipeline started this run" without a fake user row.

### Unit 4 — Tests and documentation

The exchange endpoint's verification is covered with no network and no Simulator, by injecting the
JWKS and a locally signed token:

- A token signed by the configured key, with the configured `aud` and a listed repository, is
  exchanged for a machine session that acts as that repository's org.
- A token whose `aud` is anything else is refused at the exchange, including one otherwise valid for
  a listed repository.
- A token from an unlisted repository is refused with 403, and a token whose `repository` merely
  shares a prefix with a listed entry is refused too.
- A repository listed under two orgs' `allowedRepositories` is refused as a configuration error at
  startup.
- A token in the immutable-subject format authorizes on its `repository` claim, so the two `sub`
  shapes behave identically.
- An expired token, a token with a `kid` still absent from the JWKS after the bounded refresh, and a
  token with a broken signature are each refused.
- A token whose header names `none`, and one naming HS256 signed with the RSA public key bytes, are
  both refused — the algorithm comes from configuration, never from the token.
- A token exchanged twice is accepted once; single-use holds across replicas, so a second replica
  refuses the same `jti` the first replica already consumed, not merely a token re-presented to the
  same one. A token older than the serve-side maximum age is refused even while its own `exp` is
  still in the future.
- A deployment that configures no expected `aud` refuses an otherwise valid OIDC token at the
  exchange, rather than accepting whichever audience it carries.
- An unreachable JWKS with an expired cache refuses the exchange instead of verifying against the
  stale key set.
- The minted machine session's lifetime never exceeds the presented token's own `exp`.
- `import bajutsu.serve` pulls in no `joserfc`, the same way it already pulls in none of the other
  server-only dependencies the import guard's `FORBIDDEN` set lists.
- A machine session reaches every endpoint on the allowlist and is refused on `POST /api/config`,
  `POST /api/compose`, `GET /api/config/content`, and the operator-secret endpoints. That holds the
  same way with no database wired. `POST /api/oidc/exchange` itself needs no prior session or token
  to be reached — only a verifiable OIDC token.
- Both backends (`handler.py` and `server/app.py`) enforce the machine session identically, since
  both go through `gate.py`.
- A deployment configuring an `environment`, `ref`, or `job_workflow_ref` bound refuses an otherwise
  valid token whose corresponding claim differs. For `environment` alone, it also refuses one
  whose claim is absent.
- A machine's artifact upload (`bind_artifact`) and its exists-probe (`artifact_exists`) resolve the
  org its repository is listed under, not `default`, on a multi-org deployment — and so does a
  machine-dispatched run.
- The audit record for a machine-dispatched run names the repository in its detail payload, with
  `actor_id` left null.

`docs/self-hosting.md` and its Japanese mirror gain a section covering:

- the workflow permission and the two environment variables;
- the `aud` an operator must configure, and that omitting it disables the OIDC caller shape
  entirely;
- the exchange endpoint, the machine session it mints, and that the session's time-to-live is
  capped by the presented token's own `exp`;
- the `allowedRepositories` shape, and the operator duty to update an entry when its repository is
  renamed, transferred, or deleted;
- the optional `environment` / `ref` / `job_workflow_ref` narrowing, including an `environment`
  bound refusing an absent claim the same as a differing one;
- the `pull_request_target` and fork-pull-request write-token hazards;
- that every later call in the pipeline presents the minted session, never the OIDC token itself.

A worked workflow snippet belongs there too: the GitHub-side setup is two lines, and the rest is
serve configuration.

## Alternatives considered

| Alternative | Why we did not take it |
|---|---|
| Issue a long-lived per-org CI token from the settings panel | Simpler, and it reintroduces the secret this item exists to avoid: a token to store in every pipeline, to rotate by hand, and to leak from a log. It also cannot say which repository acted — the identity gap is the point, not just the storage. |
| Reuse the shared token for CI, reopening what BE-0313 narrowed | Reverses a deliberate decision. The shared token is identity-less and full-access, so restoring it for non-worker endpoints hands every pipeline the ability to rebind a config and read secrets. |
| Give a CI identity the admin role | Four of the five endpoints CI needs are admin today, so the rank looks like a fit. It carries config rebinding, `GET /api/config/content`, and the operator-secret endpoints with it — none of which a pipeline needs, all of which it would then hold. |
| Authorize on the `sub` claim | The format has already changed for new repositories under an immutable-id rollout, and it is customizable per repository. Its shape is not serve's to assume. A prefix match on it also admits a repository whose name merely extends a listed one. The discrete claims say the same thing without either problem. |
| Authorize on the immutable numeric claims (`repository_id` / `repository_owner_id`) instead of `repository` | Those claims are immutable and unaffected by subject customization, closing the name-recycling exposure outright. The cost: a configuration nobody can read or write from the repository name alone. Adding an entry needs a lookup, and auditing config gives no hint which repository an entry means. The named form stays for that legibility, with the operator duty above as its price. |
| Use a GitHub App installation token instead of OIDC | Bajutsu already signs App JWTs for the private-repo config source (BE-0224), so the machinery is familiar. It needs an App registered and a private key distributed to the deployment, and the resulting token authenticates the App rather than the pipeline — back to a shared secret with a coarser identity. |
| Accept OIDC from any issuer out of the gate | GitLab, Buildkite, and CircleCI all issue OIDC tokens, and per-org issuer configuration would generalize this. The claim names differ per provider, so a general mapping is a larger design than the case in hand; scoping to GitHub Actions first leaves the issuer configurable and defers the mapping. |

## Progress

> Keep this current as work proceeds. The checklist mirrors the MECE work breakdown in
> *Detailed design* (one box per unit of work); the log records what changed and when
> (oldest first), linking the PRs.

- [ ] Unit 1 — Exchange the token for a machine session at `POST /api/oidc/exchange`. It verifies
      issuer, JWKS with a bounded `kid` refresh and a pinned RS256 algorithm allowlist,
      deployment-configured `aud` (fail closed if unset), and lifetime. A `jti` replay defense shared
      across replicas through the `Repository` seam, a session time-to-live capped by the token's own
      `exp`, `joserfc` declared directly in the `oauth` extra, and its verification kept in its own
      lazily-imported module so `gate.py` stays free of it.
- [ ] Unit 2 — `allowedRepositories` on `OrgConfig`, matched on the discrete claims, with the
      optional `environment` / `ref` / `job_workflow_ref` narrowing, an `environment` bound refusing
      an absent claim, and a repository listed under two orgs refused as a configuration error.
- [ ] Unit 3 — The machine session and its endpoint allowlist in `bajutsu/serve/gate.py`, enforced
      unconditionally regardless of the database, the verified org carried on the machine session
      rather than read through `org_of`, and the repository recorded in the audit entry's detail
      payload.
- [ ] Unit 4 — Tests for each seam, including the cross-replica `jti` replay test and the import-guard
      check for `joserfc`, and the self-hosting documentation.

## References

- [BE-0313 — GitHub org membership and Team-based RBAC for serve](../BE-0313-github-org-team-rbac/BE-0313-github-org-team-rbac.md)
  — the item that gave humans an identity and narrowed the shared token to worker traffic, leaving
  the machine gap this item fills.
- [BE-0051 — Serve hardening for hosting (auth, input validation)](../BE-0051-serve-hardening-for-hosting/BE-0051-serve-hardening-for-hosting.md)
  — the shared token and the request gate this item adds a third caller shape to.
- [BE-0015 — Public hosting of the web UI](../BE-0015-web-ui-public-hosting/BE-0015-web-ui-public-hosting.md)
  — the multi-tenancy and role model the machine allowlist sits beside.
- [BE-0224 — GitHub private-repo config authentication](../BE-0224-github-private-repo-config-auth/BE-0224-github-private-repo-config-auth.md)
  — a separate config-source concern that also signs a JWT (App JWTs, with `cryptography`), unrelated
  to this item's own `joserfc` dependency in the `oauth` extra.
- [BE-0160 — Credential-free worker uploads via presigned URLs](../BE-0160-worker-credential-free-uploads/BE-0160-worker-credential-free-uploads.md)
  — the same "hold no long-lived credential" posture, applied to the worker.
- [OpenID Connect reference — GitHub Docs](https://docs.github.com/en/actions/reference/security/oidc)
  — the issuer, the claim set, the immutable-subject rollout, and `include_claim_keys`.
- [OpenID Connect — GitHub Docs](https://docs.github.com/en/actions/concepts/security/openid-connect)
  — what `permissions: id-token: write` grants and how a job requests a token.
- [Using OpenID Connect in cloud providers — GitHub Docs](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-cloud-providers)
  — the request environment variables, and why the trust conditions live on the verifying side.
