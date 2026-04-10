"""Config loader.

Loads config.yaml exactly once per process and distributes it as a plain dict.
All other modules receive config via function arguments; no global imports of raw YAML.
"""

from __future__ import annotations

import hashlib
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.yaml"


@lru_cache(maxsize=1)
def load_config(path: str | None = None) -> dict[str, Any]:
    """Load the project config.yaml once and cache it.

    Financial rationale: every threshold, weight, and assumption lives in
    config.yaml so backtests and dashboards stay reproducible. Loading it
    once guarantees all engines see identical parameters within a run.
    """
    cfg_path = Path(path) if path else DEFAULT_CONFIG_PATH
    if not cfg_path.exists():
        raise FileNotFoundError(f"config.yaml not found at {cfg_path}")
    with cfg_path.open("r") as handle:
        cfg = yaml.safe_load(handle) or {}
    cfg["_meta"] = {
        "path": str(cfg_path),
        "project_root": str(PROJECT_ROOT),
        "hash": config_hash(cfg),
    }
    return cfg


def config_hash(cfg: dict[str, Any]) -> str:
    """Deterministic short hash of the config for cache key invalidation."""
    payload = {k: v for k, v in cfg.items() if k != "_meta"}
    as_json = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(as_json.encode("utf-8")).hexdigest()[:12]


def get_app_mode(cfg: dict[str, Any]) -> str:
    """Return the active app mode: 'production' or 'development'.

    The APP_MODE environment variable overrides config.yaml so that the same
    container image can be deployed across environments without a rebuild.
    """
    env_mode = os.environ.get("APP_MODE")
    if env_mode:
        return env_mode.strip().lower()
    return str(cfg.get("app", {}).get("mode", "production")).lower()


def is_production(cfg: dict[str, Any]) -> bool:
    return get_app_mode(cfg) == "production"


def reset_cache() -> None:
    """Clear the cached config (test helper only)."""
    load_config.cache_clear()
