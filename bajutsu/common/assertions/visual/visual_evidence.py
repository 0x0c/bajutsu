"""The image evidence a visual assertion leaves in the manifest and the report."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class VisualEvidence:
    """Image evidence for a visual assertion, carried into the manifest/report.

    Paths are *run-dir-relative* (the same scheme as artifacts), so the self-contained
    report and the serve UI can reference them. `baseline_name` is the YAML key into the
    baselines dir — what `approve` promotes the actual screenshot to.
    """

    baseline_name: str
    actual: str  # the captured screenshot
    baseline: str | None = None  # the baseline copy in the run dir (None if missing)
    diff: str | None = None  # the diff visualization (None when identical / missing)
    diff_pct: float | None = None
    missing: bool = False  # baseline did not exist yet (first run)
    engine: str | None = None  # the compare engine used (exact / pixelmatch; BE-0165)
    # Provenance for element-scoped comparison / selector masking (BE-0171).
    element_scoped: bool = False  # the comparison was cropped to one element's frame
    # selectors that resolved to a mask, in order (a list so it round-trips through the manifest)
    masked_selectors: list[str] = field(default_factory=list)
