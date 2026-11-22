"""One snapshot of everything: quotas, token usage and cost, and the running
sessions, as a JSON-ready dict.

Every process may make its own: Claude's and Grok's quotas are asked through
state shared by every process (see ``shared_state``), so asking often costs
the rate-limited sources nothing. The last snapshot can be saved and read back
on the next start, to show while a fresh one is made."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Optional

from agents_meter import __version__
from agents_meter.logs import Scanner, rollup
from agents_meter.quota import (QuotaService, account_from_dict, age_account, cache_dir, summarize, timezone_name,
                                write_private)
from agents_meter.tasks import list_tasks


def saved_snapshot_path() -> Path:
    return cache_dir() / "snapshot.json"


class Snapshots:
    """``claude_live`` reads Claude's quota from the endpoint ``/usage`` calls,
    with Claude Code's stored token; without it only the statusLine snapshot."""

    def __init__(self, claude_live: bool = True) -> None:
        self.scanner = Scanner()
        self.quota = QuotaService(self.scanner, claude_live)

    def _build(self, quota: dict[str, Any], refreshing: bool = False) -> dict[str, Any]:
        return {
            "version": __version__,
            "generated_at": int(time.time()),
            "timezone": timezone_name(),
            **quota,
            "usage": rollup(self.scanner.records()),
            "tasks": list_tasks(self.scanner),
            "refreshing": refreshing,
        }

    def __call__(self, force: bool = False) -> dict[str, Any]:
        """A snapshot, querying the quotas that are due (all with ``force``,
        within each source's own rate limit)."""
        return self._build(self.quota.get(force))

    def current(self, refreshing: bool) -> Optional[dict[str, Any]]:
        """A snapshot that does not wait for quotas. None until some are known."""
        quota = self.quota.current()
        return None if quota is None else self._build(quota, refreshing)

    def save(self, snapshot: dict[str, Any]) -> None:
        write_private(saved_snapshot_path(), json.dumps(snapshot))

    def restored(self) -> Optional[dict[str, Any]]:
        """The last saved snapshot, to show while a fresh one is made, its
        quotas under the freshness rules again. Tasks are left out: their
        processes may be gone."""
        now = int(time.time())
        try:
            saved = json.loads(saved_snapshot_path().read_text())
            accounts = [age_account(account_from_dict(a), now) for a in saved["accounts"]]
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            return None
        return {**saved, **summarize(accounts), "generated_at": now, "tasks": [], "refreshing": True}
