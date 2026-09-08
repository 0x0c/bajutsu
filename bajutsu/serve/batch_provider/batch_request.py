"""One scenario's worth of work for a batch cloud, with the target it runs against."""

from __future__ import annotations

from dataclasses import dataclass

from bajutsu.common.cloud.devicefarm import Platform


@dataclass(frozen=True)
class BatchRequest:
    """One scenario's worth of work for a batch cloud, with the target it runs against.

    `provider` selects the concrete `BatchProvider` from the registry; `scenario`, `target`, and
    `config` are the paths/name as they appear inside the packaged project; `platform` picks the
    device family (and, for Device Farm, the app upload type and the platform filter); `app_path` is
    the app artifact (an Android `.apk` or an iOS `.ipa`) to install on the reserved device.
    """

    provider: str
    scenario: str
    target: str
    config: str
    platform: Platform
    app_path: str
