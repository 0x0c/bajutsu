"""The top of a parsed `bajutsu.config.yaml`: team defaults and per-target config."""

from __future__ import annotations

from pydantic import Field, model_validator

from ._model import _Model
from .defaults import Defaults
from .notify_endpoint import NotifyEndpoint
from .target_config import TargetConfig


class Config(_Model):
    """A parsed `bajutsu.config.yaml`: team `defaults` and per-target config.

    The hosted multi-tenancy `orgs:` block is a `serve` concern the core does not model (BE-0129);
    `parse_config_dict` drops it before validation so a run reading an org-bearing config keeps
    working, and `bajutsu.serve.orgs` owns the org model.
    """

    defaults: Defaults = Field(default_factory=Defaults)
    targets: dict[str, TargetConfig] = Field(default_factory=dict)
    notify: list[NotifyEndpoint] = Field(default_factory=list)

    @model_validator(mode="after")
    def _targets_carry_their_platform_identifier(self) -> Config:
        # Each target must carry the identifier its resolved platform needs (iOS bundleId / web
        # baseUrl / Android package). Validated here, not on TargetConfig, because deriving the
        # platform from the backend needs `defaults` (BE-0009 Slice 4). Backward compatible: a config
        # with no `platform` derives it from the backend, so existing iOS/web targets already pass.
        # The derivation lives in the sibling `resolve` module; imported lazily to avoid a
        # schema <-> resolve import cycle at module load.
        from bajutsu.common.config.resolve import _PLATFORM_IDENTIFIER, _effective_platform

        for name, t in self.targets.items():
            backend = t.backend or self.defaults.backend
            platform = _effective_platform(t, self.defaults, backend)
            identifier = _PLATFORM_IDENTIFIER.get(platform)
            if identifier is not None and not getattr(t, identifier[1]):
                raise ValueError(f"target {name!r} (platform {platform}) needs {identifier[0]}")
        return self
