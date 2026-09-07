"""`bajutsu worker` — lease queued runs from the control plane and execute them (BE-0106).

The hosted control plane (`serve --backend=server`) inserts a job row per run; this command polls
the `/api/worker/lease` endpoint over HTTP, executes the unchanged `run_job`, uploads the run tree
(including `console.log`), and posts the result back to `/api/worker/result`. No Redis or RQ, and
**no cloud credentials** (BE-0160): every object-store touch — downloading baselines before a run,
uploading the run tree and a `record` job's authored scenario after — goes through presigned URLs
the control plane signs, so the worker needs only an HTTP client.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import typer

from bajutsu.common.backend_cli import simctl
from bajutsu.common.backends import PLATFORMS
from bajutsu.common.evidence.redaction import Redactor
from bajutsu.common.evidence.sink import RunArtifactWriter
from bajutsu.common.run_meta.files import DEFAULT_RUNS_DIR
from bajutsu.common.run_meta.object_store import content_type_for
from bajutsu.serve import InMemoryLogBus
from bajutsu.serve.capabilities import WORKER_CAPABILITIES_ENV, worker_capabilities
from bajutsu.serve.helpers import valid_sha256
from bajutsu.serve.operations.composition import materialize_composition
from bajutsu.serve.server.worker_job import WorkerIO, execute_job_spec
from bajutsu.serve.upload_artifacts import ARTIFACT_KINDS
from bajutsu.serve.uploads import find_bundle_config, materialize_bundle, validate_bundle_config

_logger = logging.getLogger("bajutsu.worker")

# Heartbeat well under the control plane's default lease timeout (DEFAULT_LEASE_TIMEOUT_SECONDS) so
# a legitimately long run is never mistaken for a dead worker and reclaimed (BE-0016).
DEFAULT_HEARTBEAT_INTERVAL = 30.0

# Per-request timeout for the presigned upload/download paths (BE-0110/BE-0160), so a stalled
# connection can't hang the worker on a single file (evidence upload runs after heartbeats stop).
_UPLOAD_HTTP_TIMEOUT = 60.0

# Name the client instead of leaving urllib's default `Python-urllib/<x.y>`: a control plane behind
# Cloudflare answers that signature with a 403 `error code: 1010` (Browser Integrity Check) before
# the request ever reaches the auth gate, so a correctly-tokened worker leases nothing forever.
_USER_AGENT = "bajutsu-worker"

# Where `_bundle_workspace` keeps one rebuilt tree per uploaded bundle, under the worker's own
# working directory. Dot-prefixed so it is never mistaken for a run's own output, nor picked up by a
# glob over the workspace. Trees nest one level deeper, per org (see `_bundle_workspace`).
_BUNDLE_CACHE_DIR = ".bundles"

# The parts a lease may sign for one bundle: the whole tree as a zip (a single-zip bind, BE-0073), or
# one object per artifact kind (a composed triple, BE-0268). A name outside this set is a broken or
# hostile lease response, never a path segment to fetch into.
_BUNDLE_PART_NAMES = frozenset({"bundle", *ARTIFACT_KINDS})


def _post_json(
    url: str, body: dict[str, Any], *, token: str | None = None, timeout: float | None = None
) -> tuple[int, Any]:
    data = json.dumps(body).encode()
    headers: dict[str, str] = {"Content-Type": "application/json", "User-Agent": _USER_AGENT}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, data=data, headers=headers)  # noqa: S310
    try:
        with urlopen(req, timeout=timeout) as r:  # noqa: S310
            raw = r.read()
            if not raw:
                return r.status, {}
            try:
                return r.status, json.loads(raw)
            except json.JSONDecodeError as e:
                # A 2xx that isn't JSON came from in front of the control plane, not from it — a proxy
                # interstitial, or an SSO login page reached through the redirect `urlopen` follows.
                # Raise it as the transport error every caller already handles: returning the text
                # would hand a `str` to callers that read the body as a mapping.
                raise URLError(f"non-JSON response from {url}: {raw[:200]!r}") from e
    except HTTPError as e:
        raw = e.read() if e.fp else b""
        if not raw:
            return e.code, {}
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            # An error page from something in front of the control plane (a proxy, Cloudflare) isn't
            # JSON. Hand back its text with the status rather than raising a decode error that buries
            # the status the caller needs to report.
            return e.code, raw.decode(errors="replace")


def _advertised_capabilities(platform: str, capabilities: str) -> list[str]:
    """The sorted capability set this worker advertises (BE-0166).

    Combines its ``--platform`` axes, the operator override (``--capabilities`` or
    `WORKER_CAPABILITIES_ENV`), and, for an iOS worker, the installed Simulator inventory. The
    Simulator probe is gated on ``ios`` so a web-only worker (the Linux container) never shells out
    to an absent ``xcrun``.
    """
    platforms = [p.strip() for p in platform.split(",") if p.strip()]
    # Fail loudly on a typo'd platform (e.g. `--platform iso`) rather than silently advertising a
    # `platform:iso` token that matches no job — the worker would otherwise poll forever leasing
    # nothing (BE-0166, "determinism first"). Same known set config's `_check_platform` validates.
    if unknown := [p for p in platforms if p not in PLATFORMS]:
        raise typer.BadParameter(
            f"invalid --platform {', '.join(unknown)}: use one of {', '.join(PLATFORMS)}"
        )
    return sorted(
        worker_capabilities(
            platforms,
            override=capabilities or os.environ.get(WORKER_CAPABILITIES_ENV),
            run=simctl.real_run if "ios" in platforms else None,
        )
    )


def worker(
    server_url: str = typer.Option(
        "",
        "--server-url",
        help="Control-plane URL (default: $BAJUTSU_SERVER_URL / http://localhost:8765)",
    ),
    token: str = typer.Option("", "--token", help="Operator token for auth"),
    poll_interval: float = typer.Option(
        2.0, "--poll-interval", help="Seconds between lease attempts when idle"
    ),
    heartbeat_interval: float = typer.Option(
        DEFAULT_HEARTBEAT_INTERVAL,
        "--heartbeat-interval",
        help="Seconds between lease heartbeats during a run (keep it under the server lease timeout)",
    ),
    worker_id: str = typer.Option("", "--worker-id", help="Worker identifier"),
    platform: str = typer.Option(
        "ios",
        "--platform",
        help="Comma-list of platforms this worker can drive (ios / web / android) — the backend "
        "axis it advertises for capability routing (BE-0166). A Mac iOS worker is 'ios'; the "
        "Playwright container is 'web'.",
    ),
    capabilities: str = typer.Option(
        "",
        "--capabilities",
        help="Extra capability tokens to advertise beyond the platform + Simulator inventory "
        "(comma/space separated, e.g. 'ios18,ipad'); also read from $BAJUTSU_WORKER_CAPABILITIES.",
    ),
) -> None:
    """Run a worker that leases queued `bajutsu run` jobs from the control plane over HTTP.

    Polls POST /api/worker/lease; on a job, runs execute_job_spec, uploads the run tree, and
    posts the result to POST /api/worker/result.
    """
    # Both drive sleeps/timeouts; a non-positive value would spin the poll or heartbeat loop hot.
    if poll_interval <= 0:
        raise typer.BadParameter("--poll-interval must be positive")
    if heartbeat_interval <= 0:
        raise typer.BadParameter("--heartbeat-interval must be positive")

    url = server_url or os.environ.get("BAJUTSU_SERVER_URL") or "http://localhost:8765"
    auth_token = token or os.environ.get("BAJUTSU_TOKEN") or None
    wid = worker_id or f"worker-{os.getpid()}"
    work = Path.cwd()
    # The capability set this worker advertises on every lease (BE-0166), computed once at startup
    # (the pool is assumed stable per worker).
    caps = _advertised_capabilities(platform, capabilities)

    typer.echo(f"bajutsu worker → polling {url}  (Ctrl-C to stop)")
    typer.echo(f"  advertising capabilities: {', '.join(caps) or '(none)'}")
    while True:
        try:
            code, body = _post_json(
                f"{url}/api/worker/lease",
                {"worker_id": wid, "capabilities": caps},
                token=auth_token,
            )
        except (URLError, OSError) as e:
            _logger.warning("lease request failed: %s", e)
            time.sleep(poll_interval)
            continue

        # Say why a lease was refused instead of polling on in silence: a rejected credential or a
        # proxy blocking the request looks exactly like an empty queue otherwise.
        if code >= 400:
            # Truncated: a refusal never self-resolves, so this repeats every poll, and a WAF's
            # error page is kilobytes of HTML — one refusal must stay one readable line.
            _logger.warning("lease refused with HTTP %s: %.200s", code, body)
            time.sleep(poll_interval)
            continue

        if code == 204 or not body.get("spec"):
            time.sleep(poll_interval)
            continue

        job_id = body["job_id"]
        spec = body["spec"]
        typer.echo(f"  leased job {job_id}")

        # A job dispatched off an uploaded bundle runs from that bundle's own tree, not the worker's
        # bare working directory, so every relative path its config names resolves. Resolved before
        # the run and reused after it, so the console log and the evidence upload read the same
        # workspace the run wrote into.
        job_work, failure = _workspace_or_failure(work, spec, body.get("bundle_urls"))
        if failure is not None:
            _post_result(url, job_id, wid, failure, auth_token)
            continue

        # The worker's object I/O is brokered by presigned URLs (BE-0160): the lease already carries
        # signed GET URLs for this run's baselines, and this io asks the control plane for signed PUT
        # URLs when uploading the run tree / authored scenario — so the worker holds no credentials.
        io = PresignedWorkerIO(
            url=url,
            auth_token=auth_token,
            job_id=job_id,
            worker_id=wid,
            baseline_urls=body.get("baseline_urls"),
        )
        bus = InMemoryLogBus()
        result, abandoned = _run_with_heartbeat(
            spec,
            job_id=job_id,
            work=job_work,
            bus=bus,
            url=url,
            wid=wid,
            auth_token=auth_token,
            heartbeat_interval=heartbeat_interval,
            io=io,
        )
        if abandoned:
            # The control plane reclaimed and likely re-leased this job to another worker; posting a
            # result would race that worker, so drop it (the re-run is the source of truth).
            typer.echo(f"  lease lost for job {job_id}; abandoning")
            continue

        run_id = result.get("runId")
        if run_id:
            _write_console_log(job_work, run_id, bus, job_id)

        _post_result(url, job_id, wid, result, auth_token)

        # Upload the run's evidence via presigned URLs the control plane signs (BE-0110): the worker
        # holds no cloud credentials of its own. Runs *after* the result is posted — heartbeats stop
        # once the run returns, so a slow upload must not delay the post and risk the lease being
        # reclaimed. Best-effort and time-bounded: a failure or stall warns and never affects the run.
        if run_id:
            _upload_evidence(
                job_work,
                run_id,
                url=url,
                auth_token=auth_token,
                evidence_prefix=str(spec.get("evidence_prefix") or ""),
            )

        # Say which way it went: a run that died on its first line ("No module named bajutsu")
        # otherwise looked exactly like a pass from this console.
        typer.echo(f"  completed job {job_id} ({'ok' if result.get('ok') else 'FAILED'})")


def _run_with_heartbeat(
    spec: dict[str, Any],
    *,
    job_id: str,
    work: Path,
    bus: InMemoryLogBus,
    url: str,
    wid: str,
    auth_token: str | None,
    heartbeat_interval: float,
    io: WorkerIO | None = None,
) -> tuple[dict[str, Any], bool]:
    """Run the job on a background thread while heart-beating its lease from this one.

    Object I/O (baseline download, run-tree/scenario upload) runs on that thread through *io*, so the
    heartbeat keeps the lease alive while a large artifact uploads. Returns ``(result, abandoned)``;
    *abandoned* is True when the control plane reclaimed the lease mid-run (HTTP 409), meaning another
    worker now owns the job and this result should be dropped.
    """
    holder: dict[str, Any] = {}

    def _run() -> None:
        try:
            job = execute_job_spec(
                spec,
                popen=subprocess.Popen,
                simctl=simctl.real_run,
                cwd=work,
                bus=bus,
                io=io,
            )
            result = job.view()
            result.pop("lines", None)
            holder["result"] = result
        except Exception as e:  # a worker keeps running past one job's failure
            _logger.exception("job %s failed", job_id)
            holder["result"] = {"ok": False, "error": str(e)}

    runner = threading.Thread(target=_run, daemon=True)
    runner.start()
    abandoned = False
    while runner.is_alive():
        runner.join(timeout=heartbeat_interval)
        if not runner.is_alive():
            break
        try:
            code, _ = _post_json(
                f"{url}/api/worker/heartbeat",
                {"worker_id": wid, "job_id": job_id},
                token=auth_token,
            )
        except (URLError, OSError) as e:
            _logger.warning("heartbeat failed for job %s: %s", job_id, e)
            continue
        if code == 409:
            abandoned = True
            runner.join()  # wait it out so this worker never runs two jobs at once
            break

    return holder.get("result", {"ok": False, "error": "worker produced no result"}), abandoned


def _write_console_log(work: Path, run_id: str, bus: InMemoryLogBus, job_id: str) -> None:
    """Write the job's buffered log to runs/<run_id>/console.log for upload.

    The log is whatever the run printed, so it goes through the sink like every other run artifact
    (BE-0331). A worker holds no secret values of its own, so the redactor is inert and only the
    sink's pattern backstop — which needs no configuration — reaches this text.
    """
    run_dir = work / DEFAULT_RUNS_DIR / run_id
    if not run_dir.is_dir():
        return
    lines = list(bus.stream(job_id, timeout=0.0))
    if not lines:
        return
    RunArtifactWriter(run_dir, Redactor(None)).write_text(
        "console.log", "".join(line for line in lines if line is not None)
    )


def _evidence_files(run_dir: Path) -> list[str]:
    """Relative POSIX paths of every real file under *run_dir* (the keys an upload endpoint signs).

    Shared by the artifact and evidence uploads. Symlinks and non-files are skipped, and each
    resolved path must stay under the run dir, so nothing outside the tree is offered for upload.
    """
    base = run_dir.resolve()
    files: list[str] = []
    for path in sorted(run_dir.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        resolved = path.resolve()
        if not resolved.is_relative_to(base):
            continue
        files.append(resolved.relative_to(base).as_posix())
    return files


def _put_file(url: str, path: Path, content_type: str, *, timeout: float | None = None) -> None:
    """Upload one file to a presigned PUT *url*, streaming it from disk.

    The Content-Type must match what the control plane signed into the URL (the presigned signature
    covers it), so send the same value. *timeout* bounds a stalled connection. The file is streamed
    (``http.client`` reads the open handle in blocks) with an explicit Content-Length, so a large run
    artifact like a video never loads wholly into memory.
    """
    headers = {"Content-Length": str(path.stat().st_size), "User-Agent": _USER_AGENT}
    if content_type:
        headers["Content-Type"] = content_type
    with path.open("rb") as body:
        req = Request(url, data=body, method="PUT", headers=headers)  # noqa: S310
        with urlopen(req, timeout=timeout):  # noqa: S310
            pass


def _get_file(url: str, dest: Path, *, timeout: float | None = None) -> None:
    """Download a presigned GET *url* into *dest*, streaming it to disk.

    Streamed rather than read whole: a baseline is a small image, but a bundle zip carries a built
    app binary and would otherwise sit in memory in full.
    """
    req = Request(url, method="GET", headers={"User-Agent": _USER_AGENT})  # noqa: S310
    with urlopen(req, timeout=timeout) as r, dest.open("wb") as out:  # noqa: S310
        shutil.copyfileobj(r, out)


def _request_upload_urls(
    url: str, endpoint: str, body: dict[str, Any], auth_token: str | None
) -> dict[str, Any]:
    """Ask the control plane for a presigned PUT URL per file (BE-0110 evidence, BE-0160 artifacts).

    Returns the ``{rel: url}`` mapping. Raises on a transport/HTTP error or a malformed response, so
    the caller decides whether to swallow it (evidence, uploaded after the verdict) or fail the run
    (artifacts). An empty mapping means the destination isn't configured — nothing to upload.
    """
    code, resp = _post_json(
        f"{url}{endpoint}", body, token=auth_token, timeout=_UPLOAD_HTTP_TIMEOUT
    )
    if code != 200:
        raise RuntimeError(f"{endpoint} returned {code}")
    urls = resp.get("urls")
    if not isinstance(urls, dict):
        raise RuntimeError(f"{endpoint} returned an unexpected response shape")  # noqa: TRY004  # invalid external payload, not a caller type error
    return urls


def _put_tree_files(run_dir: Path, urls: dict[str, Any], *, best_effort: bool) -> int:
    """PUT each ``rel -> presigned url`` file under *run_dir*, returning how many uploaded.

    Each returned key is confined under *run_dir* and required to be a string URL, so a malformed or
    hostile response can't read files outside the tree. With *best_effort* a bad entry or a failed
    PUT is logged and skipped (evidence, already past the verdict); otherwise it raises — a report
    artifact the control plane can't serve must fail the run loudly, not vanish (BE-0160).
    """
    base = run_dir.resolve()
    uploaded = 0
    for rel, put_url in urls.items():
        # Require a string key + URL and confine the key under the run dir, so a malformed or hostile
        # response can neither crash the loop (a non-string key would blow up the path-join) nor read
        # a file outside the tree. Check the types before the join so a bad key hits this guard.
        ok = isinstance(rel, str) and isinstance(put_url, str)
        src = (run_dir / rel).resolve() if ok else base
        if not ok or not src.is_relative_to(base):
            if not best_effort:
                raise RuntimeError(f"unexpected upload entry {rel!r}")
            _logger.warning("skipping unexpected upload entry %r under %s", rel, run_dir)
            continue
        try:
            _put_file(put_url, src, content_type_for(rel), timeout=_UPLOAD_HTTP_TIMEOUT)
        except Exception:
            if not best_effort:
                raise
            _logger.warning("upload failed for %s", rel)
        else:
            uploaded += 1
    return uploaded


def _post_result(
    url: str, job_id: str, worker_id: str, result: dict[str, Any], auth_token: str | None
) -> None:
    """Post a finished (or unstartable) job's result; a transport failure is logged, never raised."""
    try:
        _post_json(
            f"{url}/api/worker/result",
            {"job_id": job_id, "result": result, "worker_id": worker_id},
            token=auth_token,
        )
    except (URLError, OSError):
        _logger.exception("result post failed for job %s", job_id)


def _safe_org(org: Any) -> str:
    """*org* reduced to one safe path segment for the bundle cache, or ``default`` when unusable.

    The org travels in the job spec, so it is server-authored — but it becomes a directory name here,
    and a leased spec is still remote input. An allowlist of the characters an org id may hold keeps
    a separator or a `..` out of the path rather than trusting the value's provenance.
    """
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "", org if isinstance(org, str) else "").strip(".")
    return cleaned[:64] or "default"


def _workspace_or_failure(
    work: Path, spec: dict[str, Any], bundle_urls: Any
) -> tuple[Path, dict[str, Any] | None]:
    """The workspace to run this job from, or the failed result to post when none can be prepared.

    A job whose bundle cannot be fetched is reported as failed rather than left to crash the poll
    loop: the control plane would otherwise keep re-leasing a job this worker can never start, and
    the user would wait on a run that never returns a verdict. The returned path is meaningless when
    a failure comes back with it.
    """
    try:
        return _bundle_workspace(work, spec, bundle_urls), None
    except Exception as e:
        _logger.exception("could not materialize the job's bundle")
        return work, {"ok": False, "error": f"bundle unavailable: {e}"}


def _bundle_workspace(work: Path, spec: dict[str, Any], bundle_urls: Any) -> Path:
    """The directory to run this job from: the uploaded bundle's root, or *work* when it ships none.

    A hosted `serve` binds an uploaded zip (or a composed triple) whose config names its `appPath`
    binary, its scenarios, and its baselines relative to the bundle root. The worker holds no project
    on disk, so it fetches what the lease signed and rebuilds that tree here. Running the job *from
    the bundle root* is what makes every one of those relative paths resolve, with no rewriting on
    either side.

    The tree is keyed by the bundle id, so a second job off the same bundle reuses it and fetches
    nothing. One tree therefore serves every job off one bundle, and each run writes its `runs/` and
    console log inside it — the worker already shares one working directory across jobs, and this
    keeps that property rather than paying a copy of an app binary per job.

    Raises rather than falling back to *work*: a run started against a missing binary fails opaquely
    at install time, far from this cause (directive 2).
    """
    bundle = spec.get("bundle")
    if not isinstance(bundle, dict):
        return work
    bundle_id = bundle.get("id")
    if not valid_sha256(bundle_id):
        # Server-authored, so this is purely defensive — but the id becomes a directory name below,
        # and a leased job spec is still remote input.
        raise RuntimeError(f"job carries an invalid bundle id: {bundle_id!r}")
    urls = bundle_urls if isinstance(bundle_urls, dict) else {}
    # Scoped per org, mirroring the control plane's own `_org_uploads_dir` / `_org_compositions_dir`.
    # A content-derived id makes a cross-org hit imply identical bytes, so what this buys is not
    # isolation of the bundle: the tree is *mutable* — each run writes its `runs/` inside it — and one
    # tenant's run evidence has no business landing in another tenant's directory.
    cache = work / _BUNDLE_CACHE_DIR / _safe_org(spec.get("org"))
    tree = cache / bundle_id
    if not tree.exists():
        if not urls:
            # The lease signed nothing: a control plane with no object store configured has nowhere
            # to have stored this bundle, so no worker can ever run the job. Say that here.
            raise RuntimeError(f"job needs bundle {bundle_id}, but the lease signed no url for it")
        tree = _fetch_bundle(cache, bundle_id, bundle, urls)
    config = find_bundle_config(tree)
    if config is None:
        raise RuntimeError(f"bundle {bundle_id} holds no bajutsu.config.yaml")
    return config.parent


def _fetch_bundle(
    cache: Path, bundle_id: str, bundle: dict[str, Any], urls: dict[str, Any]
) -> Path:
    """Download the bundle's stored objects and rebuild its tree at ``cache/<bundle_id>``.

    A single-zip bind arrives as one ``bundle`` zip and goes through `materialize_bundle`; a composed
    triple arrives as its legs and goes through `materialize_composition`. Both are the control
    plane's own functions, so the worker reproduces its tree by running that code rather than
    re-implementing it, and both apply `validate_bundle_config` — the check that confines every
    target's paths to the tree (BE-0051).

    The downloads land in a temporary directory that is removed either way: the rebuilt tree is what
    persists, and a half-fetched set of parts must not look like a cache entry.
    """
    cache.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=cache, prefix=".fetch-") as raw:
        parts: dict[str, Path] = {}
        for name, url in urls.items():
            # Control-plane-authored names, re-checked because a lease response is remote input and
            # each one is joined onto a path below.
            if name not in _BUNDLE_PART_NAMES or not isinstance(url, str):
                raise RuntimeError(f"unexpected bundle part {name!r} in the lease response")
            parts[name] = Path(raw) / name
            _get_file(url, parts[name], timeout=_UPLOAD_HTTP_TIMEOUT)
        if bundle.get("artifacts") is None:
            if "bundle" not in parts:
                raise RuntimeError(f"bundle {bundle_id} was signed with no zip to fetch")
            return materialize_bundle(
                parts["bundle"], cache, bundle_id, validate=validate_bundle_config
            )
        if "config" not in parts:
            raise RuntimeError(f"composed bundle {bundle_id} was signed with no config artifact")
        return materialize_composition(
            parts["config"],
            parts.get("scenarios"),
            parts.get("binary"),
            compositions_dir=cache,
            composition_id=bundle_id,
            scenarios_filename=bundle.get("scenarios_filename"),
        )


def _download_baselines(work: Path, baseline_urls: dict[str, Any]) -> None:
    """Download each ``name -> presigned GET url`` baseline into ``work/baselines`` before the run.

    The dir is cleared first — the workspace is reused across jobs, so a baseline renamed/removed in
    storage must not linger and skew the comparison — and each name is confined under it. A download
    failure raises: a run that silently dropped its visual baselines would compare against nothing.
    """
    baselines = work / "baselines"
    if baselines.exists():
        shutil.rmtree(baselines, ignore_errors=True)
    if not baseline_urls:
        return
    base = baselines.resolve()
    for name, get_url in baseline_urls.items():
        # The control plane signs only safe baseline names, so a non-string name/URL or an escaping
        # name is a broken/hostile lease: fail loudly rather than silently drop a baseline (which
        # would leave the run comparing against nothing). Validate the types before the path-join so
        # a bad name raises this RuntimeError, not a TypeError, and never place a file outside the dir.
        if not isinstance(name, str) or not isinstance(get_url, str):
            raise RuntimeError(f"baseline {name!r} has a non-string name or URL")  # noqa: TRY004  # invalid external payload, not a caller type error
        dest = (baselines / name).resolve()
        if base not in dest.parents:
            raise RuntimeError(f"baseline {name!r} escapes the baselines dir")
        dest.parent.mkdir(parents=True, exist_ok=True)
        _get_file(get_url, dest, timeout=_UPLOAD_HTTP_TIMEOUT)


class PresignedWorkerIO:
    """The worker's object I/O over the control plane's presigned URLs (BE-0160), the `WorkerIO` seam.

    Holds no cloud credentials — only the control-plane URL, the operator token, the leased job id,
    and the signed baseline GET URLs the lease returned. The org is fixed server-side from the leased
    job, so this can never touch another tenant's prefix. Uploads fail loudly (they feed the report),
    unlike the best-effort post-verdict evidence upload.
    """

    def __init__(
        self, *, url: str, auth_token: str | None, job_id: str, worker_id: str, baseline_urls: Any
    ) -> None:
        self._url = url
        self._token = auth_token
        self._job_id = job_id
        self._worker_id = worker_id
        self._baseline_urls = baseline_urls if isinstance(baseline_urls, dict) else {}

    def download_baselines(self, work: Path) -> None:
        _download_baselines(work, self._baseline_urls)

    def upload_run(self, work: Path, run_id: str) -> None:
        run_dir = work / DEFAULT_RUNS_DIR / run_id
        if not run_dir.is_dir():
            return
        files = _evidence_files(run_dir)
        if not files:
            return
        urls = _request_upload_urls(
            self._url,
            "/api/worker/artifact-urls",
            {
                "job_id": self._job_id,
                "worker_id": self._worker_id,
                "run_id": run_id,
                "files": files,
            },
            self._token,
        )
        _put_tree_files(run_dir, urls, best_effort=False)

    def save_scenario(self, work: Path, out_path: str, app: str, ref: str) -> None:
        src = (work / out_path).resolve()
        # Confine to the workspace: a crafted spec with an absolute / `..` out_path must not read &
        # upload a host file outside it (the control plane never builds such a path).
        if work.resolve() not in src.parents:
            return
        # A `record` job that reached here was expected to author a scenario; if the file is missing,
        # fail loudly rather than report success having persisted nothing (BE-0160 / fail loud).
        if not src.is_file():
            raise RuntimeError(f"record job authored no scenario at {out_path!r}")
        code, resp = _post_json(
            f"{self._url}/api/worker/scenario-url",
            {"job_id": self._job_id, "worker_id": self._worker_id, "app": app, "ref": ref},
            token=self._token,
            timeout=_UPLOAD_HTTP_TIMEOUT,
        )
        if code != 200:
            raise RuntimeError(f"scenario-url returned {code}")
        put_url = resp.get("url")
        if not isinstance(put_url, str):
            raise RuntimeError("scenario-url returned no URL")  # noqa: TRY004  # invalid external payload, not a caller type error
        _put_file(put_url, src, content_type_for(ref), timeout=_UPLOAD_HTTP_TIMEOUT)


def _upload_evidence(
    work: Path, run_id: str, *, url: str, auth_token: str | None, evidence_prefix: str
) -> None:
    """Ask the control plane for presigned PUT URLs for this run's tree and upload each file.

    Best-effort by design (BE-0110): the run's result is already posted, so any failure here is
    logged and dropped, never raised, and every HTTP call is time-bounded so a stall can't strand the
    worker. When no evidence store is configured the endpoint returns no URLs and this uploads nothing.
    """
    run_dir = work / DEFAULT_RUNS_DIR / run_id
    if not run_dir.is_dir():
        return
    files = _evidence_files(run_dir)
    if not files:
        return
    try:
        urls = _request_upload_urls(
            url,
            f"/api/runs/{run_id}/upload-urls",
            {"files": files, "evidence_prefix": evidence_prefix},
            auth_token,
        )
    except Exception as e:
        _logger.warning("evidence upload-urls failed for run %s: %s", run_id, e)
        return
    uploaded = _put_tree_files(run_dir, urls, best_effort=True)
    if uploaded:
        typer.echo(f"  uploaded {uploaded} evidence file(s) for run {run_id}")


def register(app: typer.Typer) -> None:
    """Register this command on the Typer app."""
    app.command()(worker)
