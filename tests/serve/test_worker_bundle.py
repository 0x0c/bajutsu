"""Tests for delivering an uploaded bundle to the worker that runs the job.

A hosted control plane binds an uploaded zip (BE-0073) or a composed triple (BE-0268) and keeps the
tree on its own disk. A remote worker shares no filesystem with it, so the run used to start against
an `appPath` binary that existed nowhere on the worker and fail opaquely at install time. The lease
now signs a GET URL per stored object the bundle is made of, and the worker rebuilds the tree and
runs the job from its root. Pure packaging over a fake HTTP fetch: no network, no device.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import Any

import pytest

from bajutsu.serve.cli import worker as worker_cli

_CONFIG = (
    "defaults: { backend: [ios] }\n"
    "targets:\n"
    "  demo: { bundleId: com.example.demo, scenarios: ./scenarios, appPath: ./build/Demo.app }\n"
)
_BUNDLE_ID = "a" * 64


def _zip(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in entries.items():
            zf.writestr(name, content)
    return buf.getvalue()


def _zip_entries(prefix: str = "") -> dict[str, bytes]:
    """A bundle tree's entries: a config, a scenario, and the `appPath` binary the config names.

    *prefix* wraps every entry in one folder, the shape a zip made from a directory has — the layout
    `find_bundle_config` looks one level down for.
    """
    return {
        f"{prefix}bajutsu.config.yaml": _CONFIG.encode(),
        f"{prefix}scenarios/smoke.yaml": b"- name: a\n  steps: []\n",
        f"{prefix}build/Demo.app/Demo": b"\x7fELF",
    }


def _bundle_zip(prefix: str = "") -> bytes:
    return _zip(_zip_entries(prefix))


def _serve_urls(monkeypatch: pytest.MonkeyPatch, bodies: dict[str, bytes]) -> list[str]:
    """Stand in for the presigned GET fetch, returning *bodies* keyed by URL. Records the calls."""
    fetched: list[str] = []

    def fake_get(url: str, dest: Path, *, timeout: float | None = None) -> None:
        fetched.append(url)
        dest.write_bytes(bodies[url])

    monkeypatch.setattr(worker_cli, "_get_file", fake_get)
    return fetched


def test_a_job_with_no_bundle_keeps_the_plain_workspace(tmp_path: Path) -> None:
    # A Git-sourced or local-file run ships no bundle, so the worker's own working directory stands.
    assert worker_cli._bundle_workspace(tmp_path, {"cmd": ["run"]}, None) == tmp_path


def test_a_single_zip_bundle_becomes_the_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _serve_urls(monkeypatch, {"https://signed/bundle": _bundle_zip()})
    spec = {"bundle": {"id": _BUNDLE_ID, "artifacts": None, "scenarios_filename": None}}

    work = worker_cli._bundle_workspace(tmp_path, spec, {"bundle": "https://signed/bundle"})

    # The config's own directory is the workspace, so its relative appPath resolves from here.
    assert (work / "bajutsu.config.yaml").is_file()
    assert (work / "build" / "Demo.app" / "Demo").read_bytes() == b"\x7fELF"


def test_a_bundle_zip_wrapped_in_one_folder_resolves_to_that_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _serve_urls(monkeypatch, {"https://signed/bundle": _bundle_zip("myapp/")})
    spec = {"bundle": {"id": _BUNDLE_ID, "artifacts": None, "scenarios_filename": None}}

    work = worker_cli._bundle_workspace(tmp_path, spec, {"bundle": "https://signed/bundle"})

    assert work.name == "myapp"
    assert (work / "build" / "Demo.app" / "Demo").is_file()


def test_a_second_job_off_the_same_bundle_fetches_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The tree is keyed by the bundle id, so re-running the same bundle costs no download at all.
    fetched = _serve_urls(monkeypatch, {"https://signed/bundle": _bundle_zip()})
    spec = {"bundle": {"id": _BUNDLE_ID, "artifacts": None, "scenarios_filename": None}}

    first = worker_cli._bundle_workspace(tmp_path, spec, {"bundle": "https://signed/bundle"})
    second = worker_cli._bundle_workspace(tmp_path, spec, {"bundle": "https://signed/bundle"})

    assert first == second
    assert fetched == ["https://signed/bundle"]


def test_two_bundles_whose_binaries_share_a_name_get_separate_workspaces(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The worker reuses one tree per bundle rather than a clean directory per job, so what keeps two
    jobs apart has to be identity, not isolation. A bundle is named by the digest of its contents, so
    two builds that agree on every path and differ only in the binary's bytes are two bundles — and
    each run installs its own. Two `Demo.app` binaries under the same `appPath` is exactly the case
    a name-keyed cache would get wrong."""
    old, new = _bundle_zip(), _zip({**_zip_entries(), "build/Demo.app/Demo": b"\x7fELF-v2"})
    _serve_urls(monkeypatch, {"https://signed/old": old, "https://signed/new": new})

    def workspace(bundle_id: str, url: str) -> Path:
        spec = {"bundle": {"id": bundle_id, "artifacts": None, "scenarios_filename": None}}
        return worker_cli._bundle_workspace(tmp_path, spec, {"bundle": url})

    first = workspace("a" * 64, "https://signed/old")
    second = workspace("b" * 64, "https://signed/new")

    assert first != second
    assert (first / "build" / "Demo.app" / "Demo").read_bytes() == b"\x7fELF"
    assert (second / "build" / "Demo.app" / "Demo").read_bytes() == b"\x7fELF-v2"


def test_a_composed_triple_is_reassembled_from_its_legs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # BE-0268 stores the three artifacts separately, so the worker composes rather than unzipping a
    # whole-tree copy — which is what keeps one binary from being stored once per composition.
    fetched = _serve_urls(
        monkeypatch,
        {
            "https://signed/config": _CONFIG.encode(),
            "https://signed/scenarios": _zip({"scenarios/smoke.yaml": b"- name: a\n  steps: []\n"}),
            "https://signed/binary": _zip({"Demo": b"\x7fELF"}),
        },
    )
    spec = {
        "bundle": {
            "id": _BUNDLE_ID,
            "artifacts": {"config": "b" * 64, "scenarios": "c" * 64, "binary": "d" * 64},
            "scenarios_filename": None,
        }
    }

    work = worker_cli._bundle_workspace(
        tmp_path,
        spec,
        {
            "config": "https://signed/config",
            "scenarios": "https://signed/scenarios",
            "binary": "https://signed/binary",
        },
    )

    assert sorted(fetched) == [
        "https://signed/binary",
        "https://signed/config",
        "https://signed/scenarios",
    ]
    assert (work / "scenarios" / "smoke.yaml").is_file()
    # The binary artifact lands at the appPath the config names, extracted because it is a `.app`.
    assert (work / "build" / "Demo.app" / "Demo").read_bytes() == b"\x7fELF"


def test_a_bundle_the_lease_could_not_sign_fails_the_job(tmp_path: Path) -> None:
    # A control plane with no object store configured stored the bundle nowhere, so no worker can
    # ever run this job. Saying so here beats an opaque install-time failure (directive 2).
    spec = {"bundle": {"id": _BUNDLE_ID, "artifacts": None, "scenarios_filename": None}}
    with pytest.raises(RuntimeError, match="signed no url"):
        worker_cli._bundle_workspace(tmp_path, spec, {})


def test_an_invalid_bundle_id_is_refused_before_it_becomes_a_directory(tmp_path: Path) -> None:
    spec = {"bundle": {"id": "../escape", "artifacts": None, "scenarios_filename": None}}
    with pytest.raises(RuntimeError, match="invalid bundle id"):
        worker_cli._bundle_workspace(tmp_path, spec, {"bundle": "https://signed/bundle"})


def test_an_unexpected_part_name_in_the_lease_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Part names are control-plane-authored, but each is joined onto a path, so a lease response
    # naming something else is a broken or hostile one rather than a file to fetch.
    _serve_urls(monkeypatch, {"https://signed/x": b""})
    spec = {"bundle": {"id": _BUNDLE_ID, "artifacts": None, "scenarios_filename": None}}
    with pytest.raises(RuntimeError, match="unexpected bundle part"):
        worker_cli._bundle_workspace(tmp_path, spec, {"../etc/passwd": "https://signed/x"})


def test_a_half_fetched_bundle_leaves_no_reusable_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A failure mid-fetch must not leave something the next job mistakes for a complete bundle.
    def fake_get(url: str, dest: Path, *, timeout: float | None = None) -> None:
        raise OSError("connection reset")

    monkeypatch.setattr(worker_cli, "_get_file", fake_get)
    spec = {"bundle": {"id": _BUNDLE_ID, "artifacts": None, "scenarios_filename": None}}
    with pytest.raises(OSError, match="connection reset"):
        worker_cli._bundle_workspace(tmp_path, spec, {"bundle": "https://signed/bundle"})
    assert not (tmp_path / worker_cli._BUNDLE_CACHE_DIR / "default" / _BUNDLE_ID).exists()


def test_get_file_streams_a_body_larger_than_one_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # An app binary dwarfs the baseline images this helper first served, so it must never buffer the
    # whole response: `copyfileobj` reads in blocks, and a fake body records how it was consumed.
    payload = b"x" * (1024 * 1024)
    reads: list[int] = []

    class _Body(io.BytesIO):
        def read(self, size: int | None = -1) -> bytes:
            reads.append(-1 if size is None else size)
            return super().read(-1 if size is None else size)

        def __enter__(self) -> _Body:
            return self

        def __exit__(self, *_: Any) -> None:
            return None

    monkeypatch.setattr(worker_cli, "urlopen", lambda *_a, **_k: _Body(payload))
    dest = tmp_path / "big.zip"
    worker_cli._get_file("https://signed/bundle", dest)

    assert dest.read_bytes() == payload
    assert all(size > 0 for size in reads), "the body was read whole instead of in blocks"


def test_an_unfetchable_bundle_is_reported_as_a_failed_job(tmp_path: Path) -> None:
    # The poll loop must keep running: a job this worker can never start would otherwise be
    # re-leased forever, and the user would wait on a verdict that never arrives.
    spec = {"bundle": {"id": _BUNDLE_ID, "artifacts": None, "scenarios_filename": None}}
    work, failure = worker_cli._workspace_or_failure(tmp_path, spec, {})
    assert work == tmp_path
    assert failure is not None
    assert failure["ok"] is False
    assert "bundle unavailable" in failure["error"]


def test_a_job_that_prepares_cleanly_reports_no_failure(tmp_path: Path) -> None:
    work, failure = worker_cli._workspace_or_failure(tmp_path, {"cmd": ["run"]}, None)
    assert (work, failure) == (tmp_path, None)


def test_a_bundle_zip_with_no_config_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # `materialize_bundle`'s validation rejects this first, so the message names the missing config
    # either way — what matters is that no workspace is handed back for a run to start from.
    _serve_urls(monkeypatch, {"https://signed/bundle": _zip({"readme.txt": b"nothing here"})})
    spec = {"bundle": {"id": _BUNDLE_ID, "artifacts": None, "scenarios_filename": None}}
    with pytest.raises(ValueError, match=r"bajutsu\.config\.yaml"):
        worker_cli._bundle_workspace(tmp_path, spec, {"bundle": "https://signed/bundle"})


def test_a_single_zip_bundle_signed_without_its_zip_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _serve_urls(monkeypatch, {"https://signed/config": _CONFIG.encode()})
    spec = {"bundle": {"id": _BUNDLE_ID, "artifacts": None, "scenarios_filename": None}}
    with pytest.raises(RuntimeError, match="no zip to fetch"):
        worker_cli._bundle_workspace(tmp_path, spec, {"config": "https://signed/config"})


def test_a_composed_bundle_signed_without_its_config_leg_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _serve_urls(monkeypatch, {"https://signed/binary": _zip({"Demo": b"\x7fELF"})})
    spec = {
        "bundle": {
            "id": _BUNDLE_ID,
            "artifacts": {"config": "b" * 64, "binary": "d" * 64},
            "scenarios_filename": None,
        }
    }
    with pytest.raises(RuntimeError, match="no config artifact"):
        worker_cli._bundle_workspace(tmp_path, spec, {"binary": "https://signed/binary"})


def test_a_cached_tree_that_lost_its_config_is_refused(tmp_path: Path) -> None:
    # A tree already on disk is reused without re-validating, the same trust boundary the control
    # plane's own cache has. An entry an operator or a disk failure emptied must fail the job rather
    # than hand back a workspace with no config for the run to resolve against.
    (tmp_path / worker_cli._BUNDLE_CACHE_DIR / "default" / _BUNDLE_ID).mkdir(parents=True)
    spec = {"bundle": {"id": _BUNDLE_ID, "artifacts": None, "scenarios_filename": None}}
    with pytest.raises(RuntimeError, match="holds no bajutsu"):
        worker_cli._bundle_workspace(tmp_path, spec, {"bundle": "https://signed/bundle"})


def test_a_single_yaml_scenarios_leg_lands_under_the_name_the_bind_composed_with(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A one-file `scenarios` leg's name decides where it lands, so the worker must compose with the
    name the bind used — not with a display default. `Upload.worker_ref` carries `scenarios_name`
    for exactly this reason: composing against a picker-facing default would build a different tree
    under the same composition id."""
    _serve_urls(
        monkeypatch,
        {
            "https://signed/config": _CONFIG.encode(),
            "https://signed/scenarios": b"- name: login\n  steps: []\n",
            "https://signed/binary": _zip({"Demo": b"\x7fELF"}),
        },
    )
    spec = {
        "bundle": {
            "id": _BUNDLE_ID,
            "artifacts": {"config": "b" * 64, "scenarios": "c" * 64, "binary": "d" * 64},
            "scenarios_filename": "login.yml",
        }
    }

    work = worker_cli._bundle_workspace(
        tmp_path,
        spec,
        {
            "config": "https://signed/config",
            "scenarios": "https://signed/scenarios",
            "binary": "https://signed/binary",
        },
    )

    # `.yml` normalizes to `.yaml`, the only extension the runner's scenario listing globs.
    assert (work / "scenarios" / "login.yaml").read_bytes() == b"- name: login\n  steps: []\n"


def test_a_reactivated_composition_composes_with_no_scenarios_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The reactivation path carries no name, so the bind composed under the default. The worker has
    # to reach the same default — a synthesized display name here would write `scenarios.yaml`.
    _serve_urls(
        monkeypatch,
        {
            "https://signed/config": _CONFIG.encode(),
            "https://signed/scenarios": b"- name: a\n  steps: []\n",
            "https://signed/binary": _zip({"Demo": b"\x7fELF"}),
        },
    )
    spec = {
        "bundle": {
            "id": _BUNDLE_ID,
            "artifacts": {"config": "b" * 64, "scenarios": "c" * 64, "binary": "d" * 64},
            "scenarios_filename": None,
        }
    }

    work = worker_cli._bundle_workspace(
        tmp_path,
        spec,
        {
            "config": "https://signed/config",
            "scenarios": "https://signed/scenarios",
            "binary": "https://signed/binary",
        },
    )

    assert (work / "scenarios" / "scenario.yaml").is_file()


def test_the_bundle_cache_is_scoped_per_org(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The tree is mutable — each run writes its `runs/` inside it — so two tenants holding the same
    # bundle must not share one directory, mirroring the control plane's own org-scoped caches.
    _serve_urls(monkeypatch, {"https://signed/bundle": _bundle_zip()})

    def workspace(org: str) -> Path:
        spec = {
            "org": org,
            "bundle": {"id": _BUNDLE_ID, "artifacts": None, "scenarios_filename": None},
        }
        return worker_cli._bundle_workspace(tmp_path, spec, {"bundle": "https://signed/bundle"})

    assert workspace("acme") != workspace("globex")


def test_an_org_that_is_not_a_safe_path_segment_falls_back(tmp_path: Path) -> None:
    # The org is server-authored, but it becomes a directory name, and a leased spec is remote input.
    assert worker_cli._safe_org("../../etc") == "etc"
    assert worker_cli._safe_org("..") == "default"
    assert worker_cli._safe_org(None) == "default"
    assert worker_cli._safe_org("acme") == "acme"
