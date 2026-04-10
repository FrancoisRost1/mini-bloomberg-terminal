"""FMP endpoint catalog for the audit script.

Single source of truth for which endpoints we test. Each entry is
``(label, url, params)``. Split from fmp_endpoint_audit.py so the
runner script stays under the per file budget.
"""

from __future__ import annotations


V3 = "https://financialmodelingprep.com/api/v3"
V4 = "https://financialmodelingprep.com/api/v4"
ST = "https://financialmodelingprep.com/stable"


def endpoints(s: str) -> list[tuple[str, str, dict]]:
    return [
        # v3 endpoints currently used by terminal/data/provider_fmp.py
        (f"v3/quote/{s}",                          f"{V3}/quote/{s}", {}),
        (f"v3/quote-short/{s}",                    f"{V3}/quote-short/{s}", {}),
        (f"v3/profile/{s}",                        f"{V3}/profile/{s}", {}),
        (f"v3/historical-price-full/{s}",          f"{V3}/historical-price-full/{s}", {"serietype": "line"}),
        (f"v3/historical-price-full/{s} (full)",   f"{V3}/historical-price-full/{s}", {}),
        (f"v3/historical-chart/15min/{s}",         f"{V3}/historical-chart/15min/{s}", {}),
        (f"v3/historical-chart/1hour/{s}",         f"{V3}/historical-chart/1hour/{s}", {}),
        (f"v3/income-statement/{s}",               f"{V3}/income-statement/{s}", {"limit": "5"}),
        (f"v3/balance-sheet-statement/{s}",        f"{V3}/balance-sheet-statement/{s}", {"limit": "5"}),
        (f"v3/cash-flow-statement/{s}",            f"{V3}/cash-flow-statement/{s}", {"limit": "5"}),
        (f"v3/key-metrics/{s}",                    f"{V3}/key-metrics/{s}", {"limit": "5"}),
        (f"v3/ratios/{s}",                         f"{V3}/ratios/{s}", {"limit": "5"}),
        (f"v3/enterprise-values/{s}",              f"{V3}/enterprise-values/{s}", {"limit": "5"}),
        (f"v3/historical-market-cap/{s}",          f"{V3}/historical-market-capitalization/{s}", {"limit": "30"}),
        (f"v3/options-chain/{s}",                  f"{V3}/options-chain/{s}", {}),
        (f"v3/historical-rating/{s}",              f"{V3}/historical-rating/{s}", {}),
        (f"v3/grade/{s}",                          f"{V3}/grade/{s}", {}),
        (f"v3/social-sentiment/{s}",               f"{V3}/social-sentiment/{s}", {}),
        ("v3/stock_news",                          f"{V3}/stock_news", {"tickers": s, "limit": "5"}),
        ("v3/etf-holder/SPY",                      f"{V3}/etf-holder/SPY", {}),
        ("v3/sector-pe-ratio",                     f"{V3}/sector_price_earning_ratio", {"date": "2024-01-15"}),
        # v4 alternates
        (f"v4/historical/employee_count {s}",      f"{V4}/historical/employee_count", {"symbol": s}),
        (f"v4/insider-trading {s}",                f"{V4}/insider-trading", {"symbol": s}),
        # newer "stable" API path with different gating
        (f"stable/quote {s}",                      f"{ST}/quote", {"symbol": s}),
        (f"stable/historical-price-eod/full {s}",  f"{ST}/historical-price-eod/full", {"symbol": s}),
        (f"stable/profile {s}",                    f"{ST}/profile", {"symbol": s}),
        (f"stable/income-statement {s}",           f"{ST}/income-statement", {"symbol": s, "limit": "5"}),
        (f"stable/balance-sheet-statement {s}",    f"{ST}/balance-sheet-statement", {"symbol": s, "limit": "5"}),
        (f"stable/cash-flow-statement {s}",        f"{ST}/cash-flow-statement", {"symbol": s, "limit": "5"}),
    ]
