"""The target's resolved run-behavior defaults (BE-0177, BE-0252)."""

from __future__ import annotations

from dataclasses import dataclass, field

from bajutsu.common.scenario import AfterRule, Interrupt, Step, SystemAlertHandlingField


@dataclass(frozen=True)
class RunDefaults:
    """Per-app run-behavior defaults (BE-0177), grouped out of `Effective` (BE-0252).

    The layer the run consults when neither a CLI flag nor the scenario sets the value.
    `system_alert_handling` takes the on-disk shapes a scenario's own field does (`False`, a
    policy, or None = built-in on with the default dismissive labels); `erase` / `network` are
    the concrete built-in defaults when unset.
    """

    system_alert_handling: SystemAlertHandlingField = None
    erase: bool = False
    network: bool = True
    ios_tip_kit_handling: bool = False
    # App-wide interstitial-screen handlers (BE-0314), prepended to a scenario's own `interrupts`.
    # Empty when the target config declares none.
    interrupts: list[Interrupt] = field(default_factory=list)
    # App-wide setup/teardown phases (BE-0392). `before` is prepended to a scenario's own, `after`
    # appended after it — the merge orders `pipeline.py` applies at the `run_scenario` call site.
    # Empty when the target config declares neither.
    before: list[Step] = field(default_factory=list)
    after: list[AfterRule] = field(default_factory=list)
