"""One scenario's aggregate at a fixed fingerprint, on one OS: pass rate, duration, flakiness."""

from __future__ import annotations

from dataclasses import dataclass

from bajutsu.common.devices.os import DeviceOS


@dataclass(frozen=True)
class ScenarioStat:
    """One scenario's aggregate at a fixed fingerprint, on one OS — pass-rate, duration, flakiness.

    Keyed by the BE-0049 `(scenarioHash, name)` identity plus the parsed device OS (BE-0358), so
    neither a content edit nor an OS-version difference corrupts the old series. Pass-rate and
    `classification` come from the audit's longitudinal view (reused, not re-derived); the durations
    are aggregated here, against the same key.
    """

    scenario_hash: str
    name: str
    device_os: DeviceOS | None  # None when no run named one — see `audit.longitudinal`
    runs: int
    passed: int
    failed: int
    pass_rate: float
    avg_duration_s: float
    max_duration_s: float
    classification: str  # flaky | deterministic | unproven (BE-0049)
