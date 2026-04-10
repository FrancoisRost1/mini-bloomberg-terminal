"""Last good value cache for the header ticker tape.

The header must NEVER show n/a. If FMP fails on a refresh, we serve
the last successful value from a tiny JSON file and mark it STALE.
This file is intentionally separate from the main pickle cache so
that expired entries (which the pickle cache deletes) do not cause
the header to go blank.

The cache stores per-key dicts of {value, timestamp}. Callers decide
how to interpret freshness; this module only stores and reads.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class LastGoodCache:
    """Tiny JSON cache. Survives across sessions and never expires entries."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict[str, dict[str, Any]] = {}
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text())
            except (json.JSONDecodeError, OSError):
                self._data = {}

    def put(self, key: str, value: Any) -> None:
        self._data[key] = {"value": value, "ts": time.time()}
        try:
            self.path.write_text(json.dumps(self._data, default=str))
        except OSError:
            pass

    def get(self, key: str) -> tuple[Any, float] | None:
        entry = self._data.get(key)
        if not entry:
            return None
        return entry.get("value"), float(entry.get("ts", 0))

    def age_seconds(self, key: str) -> float | None:
        entry = self._data.get(key)
        if not entry:
            return None
        return time.time() - float(entry.get("ts", 0))
