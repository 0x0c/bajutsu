"""The categories every recorded AI call is partitioned into."""

from __future__ import annotations

# The call site a token count is attributed to, so the record report reads as a breakdown rather
# than one opaque total (BE-0194 §4). The record path spends in three places; everything else (run's
# alert guard, triage, crawl, enrich) falls in the default `other` bucket — reporting only, never on
# the pass/fail path.
CATEGORY_PLAN = "plan"  # the up-front `plan` call
CATEGORY_ACTION = "next_action"  # the per-turn `next_action` calls (the element tree + screenshot)
CATEGORY_ALERT = "alert-guard"  # the alert-guard vision calls
CATEGORY_OTHER = "other"  # any uncategorized AI call
