"""The AWS Device Farm batch provider: package, schedule one run, collect the verdict."""

from __future__ import annotations

import tempfile
import time
from collections.abc import Callable
from pathlib import Path

from bajutsu.common.cloud.devicefarm import (
    APP_UPLOAD_TYPE,
    REQUIREMENTS_TXT,
    DeviceFarmClient,
    Transfer,
    Verdict,
    build_package,
    collect_run,
    device_selection_for,
    render_test_spec,
    submit_and_collect,
)

from .batch_checkpoint import BatchCheckpoint
from .batch_request import BatchRequest


class DeviceFarmBatchProvider:
    """The AWS Device Farm concrete: package the project, schedule one run for one device, collect.

    Reserves a single device per run through a ``deviceSelectionConfiguration`` (`maxDevices` one)
    rather than a static device pool, so the Bajutsu-side budget `K` alone governs how many devices
    are held at once (BE-0336). The boto3 client and the presigned-URL transfer are injected so this
    logic runs against the in-memory fake in tests; production wires the real ones.
    """

    def __init__(
        self,
        *,
        client: DeviceFarmClient,
        transfer: Transfer,
        project_arn: str,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._client = client
        self._transfer = transfer
        self._project_arn = project_arn
        self._sleep = sleep

    def submit(
        self,
        request: BatchRequest,
        *,
        work_dir: Path,
        dest: Path,
        checkpoint: BatchCheckpoint | None = None,
    ) -> Verdict:
        """Render the one-scenario spec, package `work_dir`, submit the run, and collect the verdict.

        A `checkpoint` carrying a run ARN means this job was already scheduled before a restart: resume
        polling that run and collect it — no re-upload, no reschedule — so the in-flight run and its
        reserved device are not orphaned (BE-0336 Unit 5).
        """
        resume_arn = checkpoint.load() if checkpoint is not None else None
        if resume_arn is not None:
            return collect_run(
                self._client, self._transfer, run_arn=resume_arn, dest=dest, sleep=self._sleep
            )
        spec = render_test_spec(
            [request.scenario],
            target=request.target,
            config=request.config,
            platform=request.platform,
        )
        with tempfile.TemporaryDirectory() as staging_name:
            staging = Path(staging_name)
            spec_path = staging / "testspec.yml"
            spec_path.write_text(spec, encoding="utf-8")
            package_zip = staging / "devicefarm-package.zip"
            build_package(
                [(work_dir, ".")], package_zip, extra_texts={"requirements.txt": REQUIREMENTS_TXT}
            )
            return submit_and_collect(
                self._client,
                self._transfer,
                project_arn=self._project_arn,
                device_selection=device_selection_for(request.platform),
                app_path=Path(request.app_path),
                package_zip=package_zip,
                spec_yaml=spec_path,
                dest=dest,
                app_upload_type=APP_UPLOAD_TYPE[request.platform],
                sleep=self._sleep,
                on_scheduled=(checkpoint.save if checkpoint is not None else None),
            )
