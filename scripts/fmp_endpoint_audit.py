#!/usr/bin/env python3
"""FMP endpoint audit.

Calls every Financial Modeling Prep endpoint the terminal needs (plus
several alternates we might fall back to) and prints a single table:

    ENDPOINT  STATUS  SIZE  MS  RESULT  NOTE

Standalone. No project imports. Only requires ``requests``. Run on
Railway, on a laptop, or in CI:

    FMP_API_KEY=xxx python3 scripts/fmp_endpoint_audit.py
    FMP_API_KEY=xxx python3 scripts/fmp_endpoint_audit.py MSFT
    FMP_API_KEY=xxx python3 scripts/fmp_endpoint_audit.py AAPL --json

The endpoint catalog lives in scripts/_fmp_endpoints.py.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests

# Make _fmp_endpoints importable when the script is invoked from any cwd.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _fmp_endpoints import endpoints  # noqa: E402


def call(url: str, params: dict, api_key: str) -> dict[str, Any]:
    merged = dict(params); merged["apikey"] = api_key
    started = time.time()
    try:
        resp = requests.get(url, params=merged, timeout=15)
    except requests.RequestException as exc:
        return {"status": 0, "size": 0, "result": "FAIL", "note": f"network: {exc.__class__.__name__}", "ms": 0}
    ms = int((time.time() - started) * 1000)
    body = resp.text or ""
    size = len(body)
    code = resp.status_code
    if code == 200:
        try:
            payload = resp.json()
        except ValueError:
            return {"status": 200, "size": size, "result": "FAIL", "note": "non-json body", "ms": ms}
        return {"status": 200, "size": size, "ms": ms, **_summarize(payload)}
    if code == 401:
        return {"status": 401, "size": size, "result": "AUTH", "note": "bad or missing key", "ms": ms}
    if code in (402, 403):
        return {"status": code, "size": size, "result": "GATED", "note": f"http {code} (tier upgrade)", "ms": ms}
    if code == 429:
        return {"status": 429, "size": size, "result": "LIMIT", "note": "rate limit", "ms": ms}
    return {"status": code, "size": size, "result": "FAIL", "note": f"http {code}", "ms": ms}


def _summarize(payload: Any) -> dict[str, str]:
    if isinstance(payload, list):
        return {"result": "PASS" if payload else "EMPTY", "note": f"{len(payload)} item(s)"}
    if isinstance(payload, dict):
        if "Error Message" in payload:
            msg = str(payload["Error Message"])[:60]
            gated = any(k in msg.lower() for k in ("premium", "upgrade", "special endpoint"))
            return {"result": "GATED" if gated else "FAIL", "note": f"err: {msg}"}
        if "historical" in payload:
            hist = payload.get("historical", [])
            return {"result": "PASS" if hist else "EMPTY", "note": f"{len(hist)} bars"}
        return {"result": "PASS" if payload else "EMPTY", "note": f"{len(payload)} key(s)"}
    return {"result": "PASS", "note": "scalar"}


def fmt_size(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / (1024 * 1024):.1f} MB"


def render_table(rows: list[dict[str, Any]]) -> str:
    headers = ["ENDPOINT", "STATUS", "SIZE", "MS", "RESULT", "NOTE"]
    cols = [
        [r["endpoint"] for r in rows],
        [str(r["status"]) for r in rows],
        [fmt_size(r["size"]) for r in rows],
        [str(r["ms"]) for r in rows],
        [r["result"] for r in rows],
        [r["note"] for r in rows],
    ]
    widths = [max(len(headers[i]), max(len(c) for c in col)) for i, col in enumerate(cols)]
    sep = "  ".join("-" * w for w in widths)
    out = ["  ".join(h.ljust(widths[i]) for i, h in enumerate(headers)), sep]
    for r in rows:
        out.append("  ".join([
            r["endpoint"].ljust(widths[0]), str(r["status"]).ljust(widths[1]),
            fmt_size(r["size"]).ljust(widths[2]), str(r["ms"]).ljust(widths[3]),
            r["result"].ljust(widths[4]), r["note"].ljust(widths[5]),
        ]))
    return "\n".join(out)


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    symbol = args[0].upper() if args else "AAPL"
    api_key = os.environ.get("FMP_API_KEY", "")
    if not api_key:
        print("ERROR: FMP_API_KEY environment variable is not set.", file=sys.stderr)
        print("Usage: FMP_API_KEY=xxx python3 scripts/fmp_endpoint_audit.py [SYMBOL] [--json]", file=sys.stderr)
        return 2
    print(f"FMP ENDPOINT AUDIT")
    print(f"Symbol: {symbol}")
    print(f"Key:    {api_key[:4]}...{api_key[-4:]} ({len(api_key)} chars)")
    print()
    rows = [{"endpoint": label, **call(url, params, api_key)} for label, url, params in endpoints(symbol)]
    if "--json" in flags:
        print(json.dumps(rows, indent=2))
    else:
        print(render_table(rows))
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["result"]] = counts.get(r["result"], 0) + 1
    print()
    print(f"SUMMARY ({len(rows)} endpoints): " + " | ".join(f"{k}: {v}" for k, v in sorted(counts.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
