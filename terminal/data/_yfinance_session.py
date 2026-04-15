"""Hardened requests session for yfinance.

Yahoo Finance throttles or blocks repeated automated requests from the
same IP (common on Railway, Render, or any long-running server). This
module creates a requests.Session with:
  - Realistic browser User-Agent headers (rotated per session)
  - Retry with exponential backoff on 429/5xx responses
  - Connection pooling for efficiency
  - Configurable timeout

Usage in provider_yfinance.py:
    from terminal.data._yfinance_session import get_hardened_session

    session = get_hardened_session()
    ticker = yf.Ticker("SPY", session=session)
    df = yf.download("SPY", session=session, period="1y")
"""

import os
import random
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
]

_RETRY_STRATEGY = Retry(
    total=4,
    backoff_factor=1.5,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET", "HEAD"],
    raise_on_status=False,
)


def get_hardened_session() -> Session:
    """Create a requests Session that resists Yahoo throttling.

    Call once at provider init, then pass to every yf.Ticker() and
    yf.download() call. The session is safe to reuse across calls.
    """
    session = Session()

    # Mount retry adapter on both http and https
    adapter = HTTPAdapter(
        max_retries=_RETRY_STRATEGY,
        pool_connections=10,
        pool_maxsize=20,
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    # Set realistic browser headers
    ua = random.choice(_USER_AGENTS)
    session.headers.update({
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Cache-Control": "max-age=0",
    })

    # Optional outbound proxy. Yahoo Finance IP-bans some cloud provider
    # ranges (Railway us-west2 observed). Set YFINANCE_PROXY to a
    # residential or datacenter proxy URL (http://user:pass@host:port or
    # socks5://...) to route yfinance traffic through it.
    proxy = os.environ.get("YFINANCE_PROXY")
    if proxy:
        session.proxies = {"https": proxy, "http": proxy}

    return session
