"""Cross-run flakiness score over the serve DB run history (BE-0220, Half 1).

Mines the run records a hosted or self-hosted `serve` accumulates and ranks scenarios by how much
their verdict flips at a constant content fingerprint. It reuses `audit --history`'s exact
classification (`bajutsu.analysis.audit.classify_stability`) so the DB-backed surface and the file-backed
`audit --history` label a scenario identically.

Determinism-first, like BE-0049: this only *reports* flakiness read from recorded verdicts. It
computes no pass/fail, retries nothing, and gates nothing — nothing here is on the `run` / CI
verdict path.

The DB `Run` record carries one run-level verdict (`ok`) and one provenance stamp
(`scenario_hash`) per run, so the grouping key here is the `scenario_hash` and the metric is the
run-level verdict flip — the coarser DB counterpart to `audit --history`'s per-scenario grouping.
For the common single-scenario run the two coincide.

The key also carries the parsed device OS (BE-0358), the one component the two surfaces must share
exactly: without it a fleet running one suite across a device matrix scores every genuine OS
difference in it as flakiness. The granularities stay deliberately different — this side is per run,
the file-backed side per scenario — but the OS component and its unknown-key rule are the same, so
the two keep labelling a scenario identically.
"""

from ._functions import _TEMPLATE_DIR as _TEMPLATE_DIR
from ._functions import _as_utc as _as_utc
from ._functions import _env as _env
from ._functions import _recency_key as _recency_key
from ._functions import _record_from_manifest as _record_from_manifest
from ._functions import _render_scenario as _render_scenario
from ._functions import _representatives as _representatives
from ._functions import _scenario_name as _scenario_name
from ._functions import _score as _score
from ._functions import _window as _window
from ._functions import rank_flakiness, records_from_manifests, render, render_html
from ._shared import DEFAULT_RUN_LIMIT
from .flakiness_report import FlakinessReport
from .flaky_scenario import FlakyScenario

__all__ = [
    "DEFAULT_RUN_LIMIT",
    "FlakinessReport",
    "FlakyScenario",
    "rank_flakiness",
    "records_from_manifests",
    "render",
    "render_html",
]
