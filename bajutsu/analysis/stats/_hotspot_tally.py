from __future__ import annotations

from collections import Counter

from .hotspot import Hotspot


class _HotspotTally:
    """Accumulate per-key failure reasons and contributing run ids in one pass (BE-0102/BE-0241).

    The shared reduce the three aggregators share: each occurrence adds its reason to the key's
    tally and records the run it came from, so a hotspot can both name its top reason and link back
    to the runs behind it. Ranking is most failures first, then key for a stable order; the run ids
    are sorted and deduped so the deep link the stats page emits is deterministic.
    """

    def __init__(self) -> None:
        self._reasons: dict[str, Counter[str]] = {}
        self._run_ids: dict[str, set[str]] = {}

    def add(self, key: str, reason: str, run_id: str) -> None:
        self._reasons.setdefault(key, Counter())[reason] += 1
        ids = self._run_ids.setdefault(key, set())
        if run_id:  # a manifest with no runId still counts toward the tally, but links to nothing
            ids.add(run_id)

    def hotspots(self) -> list[Hotspot]:
        # Imported in the method, not at module load: `_functions` reads this class back, and
        # rule 5 breaks the cycle the split creates the way `Config` already breaks its own.
        from ._functions import _top_reason

        hotspots = [
            Hotspot(
                key=key,
                failures=sum(tally.values()),
                reason=_top_reason(tally),
                run_ids=tuple(sorted(self._run_ids[key])),
            )
            for key, tally in self._reasons.items()
        ]
        hotspots.sort(key=lambda h: (-h.failures, h.key))
        return hotspots
