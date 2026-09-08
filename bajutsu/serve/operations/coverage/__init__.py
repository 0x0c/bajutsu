"""Coverage-map serve operation (BE-0146).

Surfaces the deterministic `bajutsu coverage` aggregation (BE-0050) in the serve Web UI: the static
id-namespace dimension always, the endpoints-observed-vs-asserted and observed-id dimensions when a
run set is selected, and the screens-visited dimension when a crawl supplies the discovered
denominator. Read-only, deterministic, AI-free: every figure is a count over declared namespaces and
`network.json` / `elements.json` / `screenmap.json`, never a verdict and never a gate.

Two entry points share one aggregation: `coverage_view` (the view's `POST /api/coverage`, which also
carries the structured figures) and `coverage_html` (`GET /coverage`, the linkable page the other
analytics dashboards each have).
"""

from ._coverage_error import _CoverageError as _CoverageError
from ._functions import _aggregate as _aggregate
from ._functions import _artifact_paths as _artifact_paths
from ._functions import _error_page as _error_page
from ._functions import _read_json_lists as _read_json_lists
from ._functions import _runs_from_body as _runs_from_body
from ._functions import _runs_from_query as _runs_from_query
from ._functions import coverage_html, coverage_view
from ._functions import discovered_screens_via_store as discovered_screens_via_store
from ._functions import observed_identifiers as observed_identifiers
from ._functions import read_exchanges_via_store as read_exchanges_via_store
from ._functions import read_observed_ids_via_store as read_observed_ids_via_store
from ._report import _Report as _Report

__all__ = ["coverage_html", "coverage_view"]
