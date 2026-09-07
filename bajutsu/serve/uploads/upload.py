"""A bundle extracted and bound as the active config (BE-0073)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Upload:
    """A bundle extracted and bound as the active config (BE-0073). ``dir`` is the sha256-keyed
    extraction cache entry under `state.uploads_dir` (BE-0243) — independent of this one bind, so
    unbinding leaves it in place for reuse; ``config`` is the located bundle config, whose parent is
    the bundle root every run/record/crawl off it uses as its working directory.
    ``filename``/``sha256``/``size`` are the upload's provenance, recorded into each run's manifest so
    "what did this run execute?" stays answerable (DESIGN §2).

    ``sha256`` holds two different things depending on the bind (see ``artifact_shas`` below): for a
    legacy single-zip bind, a real content hash verifiable against the uploaded bytes; for a composed
    triple bind (BE-0268), a derived composition cache key with no single artifact's bytes to verify
    against. `.provenance` reports the triple instead of this field for that case, so a manifest never
    presents the derived key as if it were a verifiable hash."""

    dir: Path  # the sha256-keyed extraction cache entry (BE-0243); outlives this bind
    config: Path  # the bundle's bajutsu.config.yaml (its parent is the runs' cwd)
    filename: str
    sha256: str
    size: int
    # The org that bound this bundle (BE-0015 multi-tenancy). The single `default` org for local serve.
    org: str
    actor: str | None = None
    # Set only for a composed triple bind (BE-0268): the per-kind shas actually supplied (a subset of
    # "config"/"scenarios"/"binary" — a triple need not fill all three). `sha256` above is then the
    # composition cache key (see the class docstring), not a hash of these bytes.
    artifact_shas: dict[str, str] | None = None
    # Display filenames per supplied leg (compose-picker resume): recorded from the compose request
    # so Open config can re-seed zones without inventing names. Provenance for the UI only — layout
    # still comes from the config. A single-YAML `scenarios` leg's name also salts the composition
    # cache key, so replaying it on resume needs the same string the picker sent the first time.
    artifact_names: dict[str, str] | None = None

    @property
    def root(self) -> Path:
        """The bundle root — the config's directory, used as the runs' working directory so the
        config's relative entries (appPath / scenarios / baselines / build) resolve against it."""
        return self.config.parent

    @property
    def provenance(self) -> dict[str, str]:
        """The ``provenance`` block recorded into a run's manifest for a run off this bundle: the
        uploaded file name + zip sha256 + size, so the run's source is answerable after the sandbox
        is gone (DESIGN §2). Sizes are stringified to keep the block all-strings, like the audit log.

        A composed triple bind (BE-0268, ``artifact_shas`` set) reports ``compositionId`` and one
        ``<kind>Sha`` entry per supplied artifact instead of a top-level ``sha256`` — which would
        otherwise misleadingly imply a single hash verifiable against the composed tree's bytes."""
        if self.artifact_shas is not None:
            return {
                "source": "upload",
                "filename": self.filename,
                "size": str(self.size),
                "compositionId": self.sha256,
                **{f"{kind}Sha": sha for kind, sha in self.artifact_shas.items()},
            }
        return {
            "source": "upload",
            "filename": self.filename,
            "sha256": self.sha256,
            "size": str(self.size),
        }
