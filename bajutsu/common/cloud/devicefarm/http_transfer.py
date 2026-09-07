"""The real presigned-URL transfer, imported lazily so the base install stays SDK-free."""

from __future__ import annotations

from pathlib import Path


class HttpTransfer:
    """The real presigned-URL transfer over urllib (lazy import so the base install stays SDK-free).

    Both the CLI wrapper (`scripts/devicefarm_submit.py`) and serve's startup bootstrap
    (`bajutsu/serve/batch_bootstrap.py`) use this concrete. Keeping it here removes the duplicate
    and ensures a timeout change or retry policy reaches both callers at once.
    """

    def upload(self, url: str, path: Path) -> None:
        import urllib.request

        request = urllib.request.Request(url, data=path.read_bytes(), method="PUT")  # noqa: S310
        # An explicit timeout keeps a stalled S3 connection from hanging past the poll loops' cap.
        urllib.request.urlopen(request, timeout=300).close()  # noqa: S310 - Device Farm presigned https URL

    def download(self, url: str) -> bytes:
        import urllib.request

        with urllib.request.urlopen(url, timeout=300) as response:  # noqa: S310 - Device Farm presigned https URL
            payload: bytes = response.read()
        return payload
