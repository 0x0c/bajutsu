from __future__ import annotations

# The newest-N run window both flakiness surfaces mine from the database — the serve panel
# (`operations.reads._flakiness_report`) and the `bajutsu flakiness` CLI (`_db_flakiness`) — so the
# two rank over the same bounded history. A window large enough to read a trend, not the whole log.
DEFAULT_RUN_LIMIT = 200
