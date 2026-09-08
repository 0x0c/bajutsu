"""The install method for a browser Playwright's own downloader provides."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Playwright:
    """Provided by Playwright's own downloader: ``playwright install <browser>``."""

    browser: str
