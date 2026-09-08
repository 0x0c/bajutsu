"""Webhook notifications for run results (BE-0099).

A post-verdict side effect: builds a format-neutral summary from the run data,
filters by configured events, renders to the target format (Slack Block Kit first),
and POSTs to the configured URL. Delivery failures are logged as warnings, never able
to change the verdict or exit code. No LLM, no effect on the deterministic gate.
"""

from ._functions import _MAX_RETRIES as _MAX_RETRIES
from ._functions import _RETRY_DELAY as _RETRY_DELAY
from ._functions import _TIMEOUT_S as _TIMEOUT_S
from ._functions import _deliver as _deliver
from ._functions import _find_prior_verdict as _find_prior_verdict
from ._functions import _mask_endpoint as _mask_endpoint
from ._functions import _mask_url as _mask_url
from ._functions import _render_slack as _render_slack
from ._functions import _render_slack_start as _render_slack_start
from ._functions import _should_fire as _should_fire
from ._functions import build_summary, emit, emit_start, logger
from .failure_summary import FailureSummary
from .run_notification import RunNotification

__all__ = ["FailureSummary", "RunNotification", "build_summary", "emit", "emit_start", "logger"]
