"""FMP HTTP layer.

Pulled out of provider_fmp.py so the provider stays under the per file
budget. Owns rate limiting, retry, and 403 detection.
"""

from __future__ import annotations

import os
import time
from typing import Any

import requests


class FMPEndpointForbidden(RuntimeError):
    """FMP returned 403 (or a premium gating message) for this endpoint."""


class FMPHttp:
    """Stateless HTTP wrapper around the FMP REST API."""

    def __init__(self, config: dict[str, Any]):
        fmp_cfg = config["data"]["fmp"]
        self.base_url = fmp_cfg["base_url"]
        self.rate_limit_per_minute = int(fmp_cfg["rate_limit_per_minute"])
        retry_cfg = config["data"]["rate_limit"]
        self.max_retries = int(retry_cfg["max_retries"])
        self.backoff_base = float(retry_cfg["backoff_base_seconds"])
        self.backoff_mult = float(retry_cfg["backoff_multiplier"])
        self.api_key = os.environ.get("FMP_API_KEY", "")
        self._last_calls: list[float] = []
        self.forbidden_paths: set[str] = set()

    def throttle(self) -> None:
        now = time.time()
        self._last_calls = [t for t in self._last_calls if now - t < 60]
        if len(self._last_calls) >= self.rate_limit_per_minute:
            sleep_for = 60 - (now - self._last_calls[0]) + 0.1
            if sleep_for > 0:
                time.sleep(sleep_for)
        self._last_calls.append(time.time())

    def request(self, path: str, params: dict[str, str] | None = None) -> Any:
        if not self.api_key:
            raise RuntimeError("FMP_API_KEY environment variable not set")
        if path in self.forbidden_paths:
            raise FMPEndpointForbidden(f"FMP endpoint {path} known forbidden in this session")
        merged = dict(params or {})
        merged["apikey"] = self.api_key
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        attempt = 0
        while True:
            self.throttle()
            resp = requests.get(url, params=merged, timeout=20)
            if resp.status_code == 403:
                self.forbidden_paths.add(path)
                raise FMPEndpointForbidden(f"FMP 403 on {path}: requires tier upgrade")
            if resp.status_code == 429:
                if attempt >= self.max_retries:
                    raise RuntimeError("FMP rate limit exceeded after retries")
                time.sleep(self.backoff_base * (self.backoff_mult ** attempt))
                attempt += 1
                continue
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict) and "Error Message" in data:
                msg = data["Error Message"]
                if "Special Endpoint" in msg or "premium" in msg.lower() or "upgrade" in msg.lower():
                    self.forbidden_paths.add(path)
                    raise FMPEndpointForbidden(f"FMP gating on {path}: {msg}")
                raise RuntimeError(f"FMP error: {msg}")
            return data
