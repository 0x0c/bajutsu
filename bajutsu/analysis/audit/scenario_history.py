"""One scenario's verdict history at a fixed fingerprint on one OS — the longitudinal unit."""

from __future__ import annotations

from dataclasses import dataclass

from bajutsu.common.devices.os import DeviceOS


@dataclass(frozen=True)
class ScenarioHistory:
    """One scenario's verdict history at a fixed fingerprint *on one OS* — the longitudinal unit."""

    scenario_hash: (
        str  # the run's `provenance.scenarioHash` — the executed file's content fingerprint
    )
    name: str  # the scenario whose outcomes these are (the manifest's per-scenario `scenario`)
    # The OS these runs ran on, parsed from the per-scenario `device_runtime` (BE-0358); None when
    # no run named one. Part of the identity, so a verdict that differs *because the OS differs* is
    # two histories rather than one flaky one.
    device_os: DeviceOS | None
    runs: int  # how many accumulated runs exercised this scenario at this fingerprint
    passed: int  # runs in which it passed
    failed: int  # runs in which it failed
    pass_rate: float  # passed / runs
    classification: str  # flaky | deterministic | unproven (see `classify_stability`)
