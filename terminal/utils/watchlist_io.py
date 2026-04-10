"""Watchlist persistence.

Production: SQLite (``data/terminal.db``). Development fallback: JSON
file at ``data/watchlist.json``. Both code paths enforce the configured
max size and return sorted ticker lists so the UI renders deterministically.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

SCHEMA = "CREATE TABLE IF NOT EXISTS watchlist (ticker TEXT PRIMARY KEY, added_at TEXT)"


class WatchlistStore:
    """Abstraction over SQLite (primary) and JSON (fallback) persistence."""

    def __init__(self, config: dict[str, Any]):
        self.cfg = config
        self.max_tickers = int(config["watchlist"]["max_tickers"])
        root = Path(config["_meta"]["project_root"])
        self.db_path = root / config["watchlist"]["sqlite_db"]
        self.json_path = root / config["watchlist"]["json_fallback"]
        self._use_sqlite = True
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._init_sqlite()
        except sqlite3.Error:
            self._use_sqlite = False

    def _init_sqlite(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(SCHEMA)
            conn.commit()

    def _load_json(self) -> list[str]:
        if not self.json_path.exists():
            return []
        try:
            payload = json.loads(self.json_path.read_text())
            return sorted(set(payload.get("tickers", [])))
        except (json.JSONDecodeError, OSError):
            return []

    def _save_json(self, tickers: list[str]) -> None:
        try:
            self.json_path.parent.mkdir(parents=True, exist_ok=True)
            self.json_path.write_text(json.dumps({
                "tickers": sorted(set(tickers)),
                "updated": datetime.utcnow().isoformat(),
            }, indent=2))
        except OSError:
            pass

    def list_tickers(self) -> list[str]:
        if self._use_sqlite:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    rows = conn.execute("SELECT ticker FROM watchlist ORDER BY ticker").fetchall()
                return [r[0] for r in rows]
            except sqlite3.Error:
                self._use_sqlite = False
        return self._load_json()

    def add(self, ticker: str) -> bool:
        ticker = ticker.strip().upper()
        if not ticker:
            return False
        current = self.list_tickers()
        if ticker in current:
            return False
        if len(current) >= self.max_tickers:
            return False
        if self._use_sqlite:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        "INSERT OR IGNORE INTO watchlist(ticker, added_at) VALUES (?, ?)",
                        (ticker, datetime.utcnow().isoformat()),
                    )
                    conn.commit()
                return True
            except sqlite3.Error:
                self._use_sqlite = False
        current.append(ticker)
        self._save_json(current)
        return True

    def remove(self, ticker: str) -> bool:
        ticker = ticker.strip().upper()
        if self._use_sqlite:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cur = conn.execute("DELETE FROM watchlist WHERE ticker = ?", (ticker,))
                    conn.commit()
                return cur.rowcount > 0
            except sqlite3.Error:
                self._use_sqlite = False
        current = self._load_json()
        if ticker in current:
            current.remove(ticker)
            self._save_json(current)
            return True
        return False

    def backend(self) -> str:
        return "sqlite" if self._use_sqlite else "json"
