# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Mini Bloomberg Terminal (Project 11 of 11) -- unified investment research terminal integrating all 10 prior projects.

> Read this file fully before writing any code. This is the single source of truth for Project 11.

---

## Commands

```
# Run the app locally (development mode)
APP_MODE=development streamlit run app/app.py

# Run the app in production mode (requires FMP_API_KEY + FRED_API_KEY)
APP_MODE=production streamlit run app/app.py

# Run all tests
python3 -m pytest

# Run a single test file
python3 -m pytest tests/test_adapters/test_lbo_adapter.py

# Run a single test function
python3 -m pytest tests/test_adapters/test_lbo_adapter.py::test_base_case

# Build and run the production container
docker build -t mini-bloomberg .
docker run -p 8501:8501 --env-file .env mini-bloomberg
```

Python: `python3` (not `python`). Package manager: `pip3`.

---

## Current state

- Project scaffolded in Phase 2 with two correctness/audit passes applied.
- Parent `~/Documents/CODE/CLAUDE.md` carries cross-project universal rules and formulas. Read it before deviating from patterns.
- The data layer routes per purpose, NOT per environment. FMP (`terminal/data/provider_fmp.py`) serves single ticker stock data via the `stable/` endpoints only (the v3/ endpoints all return 403 on the Starter tier; verified with `scripts/fmp_endpoint_audit.py`). yfinance serves indices, ETFs, the breadth universe, and options chains in production AND development. FRED serves macro. There is NO silent failover between providers; each route is an explicit architectural decision. Routing lives in `terminal/data/provider_registry.py` (single_stock_provider, index_etf_provider, options_provider, macro). The SharedDataManager exposes per purpose methods: `get_stock_prices`, `get_index_prices`, `get_any_prices` (cascade for portfolio holdings of unknown type), `get_fundamentals`, `get_options_chain`, `get_macro`.
- All config flows through `terminal/config_loader.py`; PE scoring bands and regime thresholds live in `config.yaml`. Every consumed key has a config truthfulness test.
- Design system is canonical. `style_inject.py` lives at the project root and is imported flat (`from style_inject import inject_styles, TOKENS, styled_header, styled_kpi, styled_section_label, styled_divider, styled_card, apply_plotly_theme`). It is the same file across every Streamlit project in the Finance Lab. Do NOT fork it. The accent color (#E07020 Bloomberg orange) is auto-detected by walking up the filesystem and matching the folder name against a `PROJECT_ACCENTS` dict inside the file.
- File size limit: ~150 lines per Python module. Split proactively.
- Production stack: Railway (hosting) + Cloudflare (DNS) + Financial Modeling Prep (market data) + FRED (macro) + Finnhub (news) + Anthropic (LLM) + SQLite (persistence). Streamlit Community Cloud is irrelevant.

### Phase 2 audit fixes applied (reference)

- VIX is fetched from FRED `VIXCLS`, not from the equity provider.
- Options Lab uses naive `datetime.utcnow()` to avoid pandas 2.x tz-mismatch on expiry math.
- Options Lab spot price comes from `get_prices` (AV `HISTORICAL_OPTIONS` does not return `underlying_price`).
- LBO entry EBITDA in the Research pipeline is `revenue * margin` (not the previous `market_cap * margin`).
- `roe` replaces the mislabelled `roic` field across config, parsers, factor adapter, and the recommendation pipeline.
- PE scoring bands and regime thresholds moved from code into `config.yaml`.
- Interest coverage is computed in `_alphavantage_parsers.compute_ratios` and the PE red flag now fires.
- Options Lab risk-free rate is fetched from FRED via `risk_free_rate_series`.
- Phase 4 LLM is wired into the Anthropic SDK via `terminal/synthesis/llm_client.py`. The deterministic rating is locked in the prompt and any contradictory output is flagged.

### Deferred to v2

- **Portfolio Phase 3 (robustness validation)**: removed from the page. The previous implementation generated a fake trial matrix by perturbing the fitted weights with Gaussian noise, producing theatrical PBO verdicts. The robustness adapter remains available standalone for v2 to wire into a real CSCV parameter sweep.
- **Risk Parity and Black-Litterman optimizers** (already deferred in v1).
- **Cold render API budget optimization**: Market Overview can issue 20+ provider calls on a single cold render. With FMP Starter (750 req/min) this is no longer a hard limit, but pre warming on boot is still on the v2 list.

### v1.3 changes (2026-04-12)

- **Command bar**: Bloomberg-style persistent command/search bar at the top of every page. Accepts tickers, page shortcuts (market/options/lbo/comps/portfolio), and combined commands (e.g. "MSFT options"). Uses fuzzy matching via `suggest_ticker()`. Rendered in `app/command_bar.py`, integrated into `app/header.py`.
- **News switched to Finnhub**: `_news_fetch.py` now calls Finnhub `/company-news` (last 7 days) when `FINNHUB_API_KEY` is set. Falls back to yfinance silently when key is absent. Source tag updates dynamically.
- **Research page bottom layout**: 3-column row (ownership | earnings | dividends) + full-width news row. Ownership tables stack vertically. Earnings table + 180px surprise chart stack vertically. Dividends chart (180px) + yield/payout/CAGR KPIs fill the column.
- **Earnings surprise chart**: Grouped bar chart (EPS Estimate gray, EPS Actual green/red) in `_research_earnings_chart.py`.
- **Dividend section**: Annual DPS bar chart + 4 KPIs (DIV YIELD, PAYOUT RATIO, EX-DIV DATE, 5Y CAGR). Timezone crash fixed (yfinance returns tz-aware index).
- **Short interest**: SHORT % FLOAT and SHORT RATIO KPIs added to KEY STATS on Research page. Data from `_short_interest_fetch.py`.
- **LBO assumptions row**: Dense KPI row showing active scenario inputs (Entry EV, Entry Mult, EBITDA, Leverage, Exit Mult, Hold, Rev Growth) at the top of the LBO page.
- **Options chain extra columns**: Last, Chg, %Chg columns added per side. yfinance `lastPrice`, `change`, `percentChange` now flow through the provider.
- **Insider transactions fix**: `Text` field used instead of empty `Transaction` column from yfinance.
- **VIX fallback**: If FRED VIXCLS is NaN, Market Overview fetches `^VIX` from yfinance as backup. Shows STALE marker when using fallback.
- **PE score table**: Replaced `st.dataframe` with Bloomberg-style HTML table (dark background, monospace, color-coded deltas).
- **LLM memo spacing**: TLDR, timestamp, and expander now have explicit padding and separation.
- **Overlap fixes**: section_bar `overflow:hidden` clearfix for floated source tags; ownership table caption spacing increased.
- **Version bumped to 1.3.0** in `config.yaml`. Footer shows `FMP STABLE | YFINANCE | FRED | FINNHUB | ANTHROPIC`.

### Environment variables (updated)

```
FMP_API_KEY         # REQUIRED for production (single-stock market data)
FINNHUB_API_KEY     # Ticker-specific news (optional; falls back to yfinance)
ANTHROPIC_API_KEY   # LLM memo synthesis (enabled automatically when present)
FRED_API_KEY        # REQUIRED for macro data
APP_MODE            # "production" or "development" (default: production)
```

---

## 0. Live-first operating rule

This application is intended to run as an always-on hosted website, not a classroom demo.

Every infrastructure, provider, caching, and persistence decision must optimize for reliability and real usage, not for free-tier convenience.

Hard rules:
- The data layer routes per purpose, NOT per environment. Each route is an explicit architectural decision and there is no silent failover between providers.
  - Single ticker stock prices and fundamentals -> Financial Modeling Prep, stable/ endpoints only. The v3/ endpoints all return 403 on the Starter tier and are not called anywhere in the codebase.
  - Indices, ETFs, the breadth universe, options chains, and FX symbols -> yfinance, in production AND development. yfinance is NOT a dev fallback for these routes; it is the production provider for them because FMP Starter does not serve them.
  - Macro time series -> FRED. Always, in every mode.
- Routing lives in `terminal/data/provider_registry.py` which exposes single_stock_provider, index_etf_provider, options_provider, and macro. The SharedDataManager exposes per purpose methods (get_stock_prices, get_index_prices, get_any_prices, get_fundamentals, get_options_chain, get_macro). UI code must pick the right method explicitly.
- If a route's provider is unavailable, the app must show an explicit DEGRADED or DATA UNAVAILABLE state for that route only. It must never silently serve stale or unofficial data without labeling it, and it must never reroute a stock call to yfinance or an index call to FMP.
- LLM synthesis is enabled by default when ANTHROPIC_API_KEY is present. The app still works fully without it, but the intended live deployment includes continuous LLM availability.
- Persistence uses SQLite for the hosted app. JSON fallback is allowed only for local development.
- The real deployment target is a paid hosted container environment (cloud VM, Railway, Render, etc.). Streamlit Community Cloud is not a target for the real application and must not influence architecture decisions.
- Cache aggressively. The terminal must stay cheap and responsive on low tier API plans (FMP Starter is 750 req/min, more than enough for single user usage).

Production stack: Railway (hosting) + Cloudflare (domain/DNS) + FMP for single ticker stock data (stable/) + yfinance for indices, ETFs, breadth, options, and FX + FRED (macro) + Anthropic (LLM) + SQLite (persistence). Streamlit Community Cloud is irrelevant.

---

## 1. What this project is

A focused, institutional-grade investment research terminal built in Streamlit. Four workspaces, each answering a real investor question:

- **Market**: What regime are we in?
- **Research**: Should I own this?
- **Analytics**: What is the risk / value / transaction math?
- **Portfolio**: How should I allocate capital, and is the allocation stable?

This is NOT a collection of dashboards stitched together. It is a single research workstation with shared navigation, shared data layer, and contextual tools embedded where they belong.

### The interview narrative

"I built 10 standalone financial engines covering LBO modeling, PE screening, factor analysis, volatility regime detection, momentum signals, options pricing, portfolio optimization, strategy robustness testing, and an AI research agent. Then I unified all of them into a single Bloomberg-style terminal where an analyst can go from market overview to deep-dive research to portfolio construction without switching tools. Every analytical result is deterministic and traceable. The AI layer is optional."

---

## 2. Architecture overview

### Navigation model

Multi-page Streamlit with `st.navigation` organized into 4 institutional sections:

```
Sidebar (fixed, minimal, Bloomberg-like):
  MARKET
    Market Overview
  RESEARCH
    Ticker Deep Dive
  ANALYTICS
    Options Lab
    LBO Quick Calc
    Comps & Relative Value
  PORTFOLIO
    Portfolio Builder
```

Rules:
- No cute labels. No emoji in nav. Terminal-style naming only.
- Persistent global header on every page with: ticker search bar, active ticker display, watchlist quick-access, market context strip (SPY/VIX/DXY mini-display).
- Research and Analytics react to the global ticker bar.
- Market and Portfolio maintain their own independent context.
- Sidebar is fixed and minimal. No 10+ page sprawl.

### Global state model

Maintain four separate state concepts in session_state (UI context only):

```python
st.session_state.active_ticker      # str, drives Research + Analytics
st.session_state.watchlist           # list[str], persistent via SQLite (production) or JSON (dev)
st.session_state.active_portfolio    # dict, drives Portfolio workspace
st.session_state.market_context      # dict, cached macro snapshot for header
```

Do NOT collapse the product into one ticker variable.

### File structure

```
mini-bloomberg-terminal/
  CLAUDE.md
  config.yaml
  requirements.txt
  Dockerfile
  .streamlit/
    config.toml
  app/
    __init__.py
    app.py                          # entry point, st.navigation, global header
    command_bar.py                  # Bloomberg-style command/search bar (ticker + page navigation)
    header.py                       # global header component (ticker bar, watchlist, market strip)
    header_status.py                # market status indicator
    header_tape.py                  # scrolling market tape
    header_tape_batch.py            # batched tape data fetching
    header_sidebar_toggle.py        # sidebar toggle button
    sidebar_ticker.py               # sidebar ticker display
    footer.py                       # page footer
    density_css.py                  # UI density/compactness CSS injection
    pages/
      __init__.py
      market_overview.py            # MARKET workspace (delegates to _market_* helpers)
      ticker_deep_dive.py           # RESEARCH workspace (delegates to _research_* helpers)
      options_lab.py                # ANALYTICS: Options Lab (delegates to _options_* helpers)
      lbo_quick_calc.py             # ANALYTICS: LBO Quick Calc (uses _lbo_helpers)
      comps_relative_value.py       # ANALYTICS: Comps (delegates to _comps_* helpers)
      portfolio_builder.py          # PORTFOLIO workspace (delegates to _portfolio_* helpers)
      _market_*.py                  # ~6 helper modules (breadth, grid, kpi, regime, etc.)
      _research_page_helpers.py     # phase1 chart + stats, re-exports for phase2-4
      _research_engine_grid.py      # phase2 engine card grid
      _research_engine_renderers.py # individual engine card renderers + LLM memo
      _research_visuals.py          # phase3 recommendation bar + composite score
      _research_financials.py       # financials table + 52w range bar
      _research_analyst.py          # analyst consensus (price targets, ratings)
      _research_news.py             # news feed via Finnhub (yfinance fallback)
      _research_ownership.py        # institutional holders + insider transactions
      _research_earnings.py         # earnings calendar + history table
      _research_earnings_chart.py   # EPS estimate vs actual grouped bar chart
      _research_dividends.py        # annual DPS bar chart + yield/payout/CAGR KPIs
      _options_chain.py             # full chain table with ITM/ATM highlighting
      _options_payoff.py            # single-leg payoff chart with spot/breakeven lines
      _options_*.py                 # ~4 more helpers (greeks, surface, strategies, etc.)
      _portfolio_*.py               # ~5 helper modules (build, decompose, validate, etc.)
      _comps_*.py                   # ~5 helper modules (peers, valuation, ma, etc.)
      _lbo_helpers.py               # LBO page helper
  terminal/
    __init__.py
    config_loader.py                # load config.yaml once, pass as dict
    data/
      __init__.py
      provider_interface.py         # MarketDataProvider ABC
      provider_fmp.py               # Financial Modeling Prep: PRODUCTION provider (fully implemented)
      provider_yfinance.py          # yfinance: indices, ETFs, breadth, options, FX (prod AND dev)
      provider_polygon.py           # Polygon.io: future upgrade stub (interface-ready, not wired)
      provider_fred.py              # FRED API for macro data (always used, not a fallback)
      provider_registry.py          # provider selection, mode enforcement, no silent fallback
      schemas.py                    # normalized dataclasses: PriceData, Fundamentals, MacroData, OptionsChain
      cache.py                      # cache layer with config-hash keys, aggressive TTLs
      _fmp_http.py                  # FMP HTTP client with rate limiting
      _fmp_parsers.py               # FMP response normalization
      _fmp_ratios.py                # FMP ratio computation helpers
    managers/
      __init__.py
      data_manager.py               # SharedDataManager (st.cache_resource)
      analytics_manager.py          # AnalyticsManager (st.cache_data for expensive engine outputs)
      _macro_fallback.py            # fallback logic for macro data gaps
      _news_fetch.py                # Finnhub news (primary) with yfinance fallback
      _analyst_fetch.py             # yfinance analyst consensus fetcher
      _ownership_fetch.py           # yfinance institutional holders + insider transactions
      _earnings_fetch.py            # yfinance earnings calendar + history
      _dividends_fetch.py           # yfinance dividend history + yield/payout/ex-date stats
      _short_interest_fetch.py      # yfinance short interest metrics
    adapters/
      __init__.py
      research_adapter.py           # wraps P10 orchestrator pipeline
      lbo_adapter.py                # wraps P1 LBO core (base case snapshot)
      pe_scoring_adapter.py         # wraps P2 percentile scoring + valuation logic
      factor_adapter.py             # wraps P3 factor exposure snapshot
      ma_comps_adapter.py           # wraps P4 M&A comps + deal browser
      regime_adapter.py             # wraps P5 volatility regime detection
      tsmom_adapter.py              # wraps P6 TSMOM signal snapshot
      robustness_adapter.py         # wraps P7 robustness validation (PBO, DSR, plateau)
      optimizer_adapter.py          # wraps P8 MV + HRP optimizers
      options_adapter.py            # wraps P9 Greeks, IV, vol surface
      _research_sub_scores.py       # sub-score computation helpers for research pipeline
      _ma_seed.py                   # M&A synthetic seed data generator
    engines/
      __init__.py
      pnl_engine.py                 # P&L interpretation layer (shared across workspaces)
      recommendation_engine.py      # deterministic recommendation logic (from P10)
      regime_engine.py              # regime classification for Market workspace
      breadth_engine.py             # market breadth metrics
    utils/
      __init__.py
      formatting.py                 # number formatting, KPI helpers (single-line HTML only)
      chart_helpers.py              # Plotly chart factory with Bloomberg theme + interpretation callouts
      error_handling.py             # degraded state display, error boundaries
      watchlist_io.py               # SQLite persistence (production) with JSON fallback (local dev)
      sparkline.py                  # inline sparkline chart generation
      marquee.py                    # scrolling marquee/tape components
      tape_helpers.py               # market tape data helpers
      density.py                    # UI density configuration
      styling.py                    # additional styling utilities
      skeletons.py                  # loading skeleton placeholders
      sector_peers.py               # sector peer lookup for comps
      cache_utils.py                # shared caching utilities
      tradingview.py                # TradingView widget integration
      ticker_lookup.py              # smart ticker validation + search
      _ticker_symbols.py            # ticker symbol constants for validation
  tests/
    __init__.py
    test_adapters/
    test_data/
    test_engines/
    test_managers/
    test_pages/
  data/
    raw/
    processed/
    cache/
  docs/
    analysis.md
  outputs/
```

Rules:
- One file = one responsibility. main.py (app.py) orchestrates only.
- No file exceeds ~150 lines. Split proactively.
- Inside `app/` use **absolute** imports (`from app.header import ...`, `from app.pages._helpers import ...`) NOT relative imports. Streamlit loads the entry script and every page via `st.Page("pages/X.py")` as a top-level script (no parent package), so relative imports raise `ImportError: attempted relative import with no known parent package` and crash the app on Railway. This was a real production crash on the first deploy. Do NOT revert to relative imports.
- Every entry-point file in `app/` (the entry script `app.py` and every page in `app/pages/`) MUST bootstrap the project root onto `sys.path` BEFORE any project import. The pattern: `_PROJECT_ROOT = Path(__file__).resolve().parents[2]` (or `.parent.parent` for `app/app.py`), then `sys.path.insert(0, str(_PROJECT_ROOT))`. This makes `app.*` and `terminal.*` resolvable when Streamlit runs the file directly.
- **Page helper module pattern**: Each main page file (e.g., `market_overview.py`) stays under 150 lines by delegating to underscore-prefixed helper modules (e.g., `_market_kpi.py`, `_market_regime.py`, `_market_breadth.py`). There are ~35 helper modules total across all pages. Only the main page files are registered with `st.Page()`; helpers are imported by the main page.
- **Docker entrypoint**: The Dockerfile runs `start.sh` (not `streamlit run` directly). Check `start.sh` for any pre-launch setup.

### Test fixtures

`tests/conftest.py` provides three session-scoped fixtures used across all test files:
- `config`: loads `config.yaml` once via `load_config()`
- `synthetic_prices`: 400-day OHLCV DataFrame (seed=42) for any test needing price data
- `synthetic_returns_matrix`: 500x5 returns DataFrame (seed=7) for portfolio/optimizer tests

---

## 3. Data architecture

### Provider-agnostic data layer

All data flows through a `MarketDataProvider` abstract interface:

```python
class MarketDataProvider(ABC):
    """Abstract interface for market data. All providers return normalized schemas."""

    @abstractmethod
    def get_prices(self, ticker: str, period: str = "1y") -> PriceData:
        """Fetch OHLCV price history. Returns normalized PriceData."""

    @abstractmethod
    def get_fundamentals(self, ticker: str) -> Fundamentals:
        """Fetch financial statements + key ratios. Returns normalized Fundamentals."""

    @abstractmethod
    def get_macro(self, series: list[str]) -> MacroData:
        """Fetch macro time series. Returns normalized MacroData."""

    @abstractmethod
    def get_options_chain(self, ticker: str) -> OptionsChain:
        """Fetch options chain with Greeks-ready fields. Returns normalized OptionsChain."""
```

### Normalized schemas (in `terminal/data/schemas.py`)

```python
@dataclass
class PriceData:
    ticker: str
    prices: pd.DataFrame          # columns: open, high, low, close, volume, adj_close
    currency: str                  # ISO currency code
    provider: str                  # which provider returned this
    as_of: datetime                # timestamp of fetch
    period: str                    # requested period

@dataclass
class Fundamentals:
    ticker: str
    income_statement: pd.DataFrame    # annual, columns: revenue, ebitda, net_income, etc.
    balance_sheet: pd.DataFrame       # annual
    cash_flow: pd.DataFrame           # annual
    key_ratios: dict                  # pe_ratio, ev_ebitda, roic, ebitda_margin, fcf_conversion, etc.
    market_cap: float
    sector: str
    industry: str
    provider: str
    as_of: datetime

@dataclass
class MacroData:
    series: dict[str, pd.Series]      # series_id -> time series
    provider: str
    as_of: datetime

@dataclass
class OptionsChain:
    ticker: str
    spot: float
    chains: dict[str, pd.DataFrame]   # expiry_date_str -> DataFrame with strike, bid, ask, volume, oi, type
    provider: str
    as_of: datetime
```

### Provider registry and mode enforcement

```python
# provider_registry.py
# - Reads config.yaml for mode: "production" or "development"
# - production mode: FMP only. If unavailable, DEGRADED state. No silent yfinance fallback.
# - development mode: yfinance allowed, with visible DEV MODE indicator.
# - FRED is always used for macro in both modes.
# - Architecture preserves easy swap to Polygon: change config provider key + add API key.
```

### Provider implementations

1. **provider_fmp.py**: PRODUCTION provider. Fully implemented Financial Modeling Prep integration using their documented v3 REST API. Covers quotes, daily prices, company profile, annual income statement, balance sheet, cash flow, and options chain (when available). API key loaded from FMP_API_KEY env var. Rate limit: 750 requests/minute on Starter tier. Throttle is enforced at 300/min as a safety margin. All responses normalized into terminal schemas. This is NOT a stub.
2. **provider_yfinance.py**: LOCAL DEVELOPMENT ONLY. Wraps yfinance into normalized schemas for offline/dev work. Known limitations documented (scraping fragility, unreliable dividendYield, no SLA). Excluded from production config by default. If yfinance is serving data in production mode, the app must display a visible DEV MODE warning.
3. **provider_polygon.py**: Future upgrade path to Polygon.io. Implements the same MarketDataProvider interface. Not wired in v1, but the interface is ready so swapping providers requires only a config change and API key.
4. **provider_fred.py**: FRED API for macro data. Required in all modes (free API key). Handles: Treasury yields, credit spreads, VIX history, GDP, CPI, unemployment. Dedicated source, not a fallback.

### Caching strategy

```
SharedDataManager (st.cache_resource):
  - Singleton per session
  - Holds provider instances
  - Manages cache for prices, fundamentals, macro
  - Cache keys: (ticker, data_type, config_hash, date)
  - TTL-based expiry from config.yaml
  - Never re-fetches within TTL window

AnalyticsManager (st.cache_data):
  - Caches expensive engine outputs (LBO, factor exposure, options Greeks, etc.)
  - Cache keys include config_hash so config changes invalidate correctly
  - Progressive loading support: returns partial results while engines still running

session_state:
  - UI context ONLY: active_ticker, watchlist, active_portfolio, market_context
  - Never used as data cache
```

### Failure handling

- If provider fails: show explicit DEGRADED badge on affected widgets. Never silently break charts.
- If all providers fail for a ticker: show DATA UNAVAILABLE state with explanation.
- Never crash the app due to data failure. Every data call is wrapped in try/except with fallback rendering.
- Rate limit handling: exponential backoff with max retries from config.

---

## 4. Adapter architecture

Every adapter follows a standard pattern:

```python
class TerminalAdapter:
    """
    Base pattern for all adapters.

    Each adapter must declare:
    - SOURCE_PROJECT: str        (e.g., "P1: LBO Engine")
    - SIMPLIFICATIONS: list[str] (what was removed vs full project)
    - INPUT_SCHEMA: dict         (what the adapter expects)
    - OUTPUT_SCHEMA: dict        (what the adapter returns)
    """
```

### Adapter inventory

| Adapter | Source | Vendored kernel | Simplifications | Terminal output |
|---------|--------|----------------|-----------------|-----------------|
| research_adapter | P10 | orchestrator.run_pipeline | Full pipeline, no simplification | research_packet dict |
| lbo_adapter | P1 | LBO core engine (base case) | Base case only, no Monte Carlo, no full scenario lab | lbo_snapshot dict (IRR, MOIC, debt schedule) |
| pe_scoring_adapter | P2 | percentile scoring + valuation | Single-ticker scoring, no universe screen | valuation_metrics dict |
| factor_adapter | P3 | factor computation | Snapshot exposure, not full backtest | factor_exposure dict (5 factor scores) |
| ma_comps_adapter | P4 | deal queries + regime classification | Query interface only, no full DB rebuild | comps_table DataFrame, regime_context dict |
| regime_adapter | P5 | regime detection (rule-based composite) | Rule-based only, no HMM retraining | regime_state dict (regime label, confidence, signals) |
| tsmom_adapter | P6 | TSMOM signal computation | Signal snapshot, no full backtest | momentum_signals dict |
| robustness_adapter | P7 | PBO + DSR + plateau detection | Runs on provided trial matrix, no trial generation | robustness_report dict (PBO, DSR, verdict) |
| optimizer_adapter | P8 | MV + HRP optimizers | 2 of 4 optimizers, no BL/RP in v1 | weights dict, risk_decomposition dict |
| options_adapter | P9 | BS Greeks, IV extraction, vol surface | No delta hedging sim in v1 | greeks dict, iv_surface DataFrame |

### Adapter rules

- UI layer calls adapters, never raw project internals.
- Each adapter converts normalized terminal schemas into engine-specific inputs and back.
- If an adapter's engine fails, it returns a standardized error dict with `status: "failed"` and `reason: str`.
- No duplicate logic across adapters. Shared utilities go in `terminal/utils/`.

---

## 5. P&L interpretation layer

The P&L engine is NOT a standalone product. It is an interpretation layer used contextually across workspaces:

### Usage by workspace

| Workspace | P&L usage |
|-----------|-----------|
| Analytics (Options Lab) | Option payoff diagrams, Greeks P&L scenarios, breakeven analysis |
| Analytics (LBO Quick Calc) | Entry-to-exit equity value bridge, IRR sensitivity |
| Portfolio | Attribution (what drove returns), realized vs expected performance decomposition |
| Research | Structured scenario payoff inputs for LLM memo (bull/base/bear with dollar outcomes) |

### P&L engine interface

```python
# pnl_engine.py

def compute_option_payoff(spot: float, strike: float, premium: float,
                          option_type: str, quantity: int = 1) -> pd.DataFrame:
    """Payoff diagram data for a single option leg."""

def compute_option_scenario(greeks: dict, spot_range: np.ndarray,
                            vol_shift: float = 0, time_decay_days: int = 0) -> pd.DataFrame:
    """Greeks-based P&L scenario across spot range with optional vol/time shifts."""

def compute_lbo_equity_bridge(lbo_snapshot: dict) -> dict:
    """Entry-to-exit equity value waterfall: entry EV, debt paydown, EBITDA growth, multiple expansion."""

def compute_portfolio_attribution(weights: dict, returns: pd.DataFrame,
                                  factor_exposures: pd.DataFrame) -> dict:
    """Factor-based return attribution: what drove the portfolio's P&L."""

def compute_scenario_payoffs(ticker_data: dict, scenarios: list[dict]) -> list[dict]:
    """Bull/base/bear scenario outcomes with dollar P&L. Used as structured LLM input."""
```

---

## 6. Workspace specifications

### 6.1 MARKET: Market Overview

**Investor question:** What regime are we in?

**Layout:**
```
[Global Header: ticker bar | watchlist | market context strip]
---------------------------------------------------------
| Global Indices Strip (SPY, QQQ, DJI, IWM, EFA, EEM)  |
---------------------------------------------------------
| Rates & Yields        | Volatility & Risk             |
| US 2Y, 10Y, 30Y      | VIX level + term structure    |
| 2s10s spread          | Credit spread (HY OAS)        |
| Fed funds rate        | Equity put/call ratio         |
---------------------------------------------------------
| Cross-Asset Dashboard                                  |
| Equities | Bonds | Commodities | FX                   |
| (normalized returns, trend, regime label per asset)    |
---------------------------------------------------------
| Regime Indicator (from P5)                             |
| Current regime: RISK_ON / NEUTRAL / RISK_OFF           |
| Composite signals: trend, vol stress, drawdown, credit |
| Regime history chart (12mo)                            |
---------------------------------------------------------
| Market Breadth                                         |
| % above 200d MA | advance/decline | new highs/lows    |
---------------------------------------------------------
| Interpretation callout: 1-2 sentences on regime state  |
---------------------------------------------------------
```

**Data sources:**
- Indices: market data provider (SPY, QQQ, DJI, IWM, EFA, EEM)
- Rates: FRED (DGS2, DGS10, DGS30, FEDFUNDS, T10Y2Y)
- Volatility: market data provider (^VIX) + FRED (BAMLH0A0HYM2 for HY spread)
- Commodities: market data provider (GLD, USO, DBC)
- FX: market data provider (DXY/UUP)
- Breadth: computed from a broad universe prices (configurable in config.yaml)

**Regime engine:**
- Uses regime_adapter (P5) for composite regime classification
- Rule-based only (no HMM retraining at runtime)
- Signals: trend direction, vol stress level, drawdown depth, credit conditions
- Output: regime label + confidence + signal decomposition

### 6.2 RESEARCH: Ticker Deep Dive

**Investor question:** Should I own this?

**Progressive loading sequence:**
```
Phase 1 (immediate, <2s):
  - Price chart (1Y default, configurable)
  - Key stats card (market cap, P/E, EV/EBITDA, dividend yield, 52w range)
  - Financial summary (revenue, EBITDA, margins, FCF, debt)

Phase 2 (engine loading, 2-10s):
  - Engine cards appear one by one as they complete
  - Each card shows loading / success / failed / degraded status
  - Engines: PE scoring, factor exposure, vol regime, LBO snapshot, TSMOM signal, options Greeks

Phase 3 (recommendation, after engines):
  - Deterministic recommendation: BUY / HOLD / SELL / INSUFFICIENT_DATA
  - Composite score breakdown: valuation (35%), quality (25%), momentum (20%), risk (20%)
  - Signal decomposition per sub-score
  - Rule trace: which rules fired, any override reasons
  - Confidence grade (A-F)

Phase 4 (optional LLM, if enabled):
  - LLM memo synthesis (Claude API)
  - LLM receives deterministic rating in prompt, cannot override it
  - Memo sections: thesis, valuation, quality, momentum, risk, conclusion
  - Rendered only after Phase 3 is complete
```

**Data gates (from P10):**
- HARD FAIL if no price data OR no financials (show error state)
- DEGRADED if SEC filings missing (amber warning, confidence drops)
- INSUFFICIENT DATA if < 2 valid core engines OR overall confidence < 0.4

**Scenario payoffs (P&L layer):**
- Bull/base/bear scenario cards with dollar outcomes
- Fed as structured input to LLM memo if enabled

### 6.3 ANALYTICS: Options Lab

**Investor question:** What is the options risk/reward math?

**Content:**
- Greeks dashboard: Delta, Gamma, Theta, Vega, Rho for selected strike/expiry
- IV extraction from live chain (Brent solver from P9)
- Vol surface visualization (log-moneyness x time to expiry)
- 25-delta skew metrics (risk reversal, butterfly)
- Payoff diagram (single leg or simple multi-leg)
- P&L scenario: Greeks-based P&L across spot range with vol/time shifts

**Inputs:** Ticker from global bar, user selects expiry + strike(s)

### 6.4 ANALYTICS: LBO Quick Calc

**Investor question:** What are the PE return mechanics for this target?

**Content:**
- Base case LBO snapshot (from P1 adapter)
- Key outputs: entry EV, sponsor equity, IRR, MOIC, exit EV
- Debt schedule summary (not full year-by-year in v1)
- Equity bridge waterfall (P&L layer): entry to exit value decomposition
- Sensitivity table: IRR across exit multiple x EBITDA growth grid
- User-adjustable inputs: entry multiple, leverage, growth rate, exit multiple (all defaulted from config)

### 6.5 ANALYTICS: Comps & Relative Value

**Investor question:** How does this name compare to its peers?

**Content:**
- Peer comps table: EV/EBITDA, P/E, margins, growth, leverage for sector peers
- Relative valuation: where the active ticker sits vs sector distribution
- Historical valuation range (current vs 5Y percentile)
- M&A comps from P4: relevant deal multiples in the sector
- Valuation scoring from P2: percentile rank across key metrics

### 6.6 PORTFOLIO: Portfolio Builder

**Investor question:** How should I allocate, and is it stable?

**Workflow (three-phase):**

```
Phase 1: BUILD
  - Input: ticker list (from watchlist or manual entry) + constraints
  - Run MV optimizer (from P8)
  - Run HRP optimizer (from P8)
  - Display: weights comparison, efficient frontier, risk decomposition
  - Herfindahl concentration metric

Phase 2: DECOMPOSE
  - Factor attribution (from P3 adapter): which factors explain the portfolio
  - Sector/asset class decomposition
  - Realized vs expected performance comparison (P&L layer)

Phase 3: VALIDATE
  - Robustness check (from P7 adapter): PBO, deflated Sharpe, plateau fraction
  - IS vs OOS consistency diagnostics
  - Verdict: ROBUST / LIKELY ROBUST / BORDERLINE / LIKELY OVERFIT / OVERFIT
  - Robustness is tied to the selected portfolio, not shown as an abstract detached lab
```

---

## 7. Watchlist

- **Production:** SQLite persistence (`data/terminal.db`, `watchlist` table)
- **Development fallback:** JSON file (`data/watchlist.json`) if SQLite is unavailable
- Visible from header or sidebar, not buried
- Clicking a watchlist ticker jumps directly into Research on that ticker
- Max watchlist size: configurable (default 20)
- SQLite schema: `CREATE TABLE watchlist (ticker TEXT PRIMARY KEY, added_at TEXT)`

---

## 8. UI and design standards

### Bloomberg dark mode

- Copy `style_inject.py` and `.streamlit/config.toml` from DESIGN.md
- Dark background (#0E1117 or as per DESIGN.md)
- Amber/orange accent for key metrics
- Monospace for numbers/data
- No emoji anywhere in the UI or nav
- No m-dashes in any user-facing text
- No cute labels, no ornamental widgets, no demo-style clutter

### Chart standards

- All charts use Plotly with Bloomberg dark theme
- Every chart has an explicit string title (never dict, never "undefined")
- Every axis has explicit units (%, $, years, annualized, bps, etc.)
- Every chart has an interpretation callout: 1-2 sentences explaining what it means financially
- Use observation / interpretation / implication format for callouts
- Model limitations visible in sidebar or section header where relevant

### KPI display

- Use single-line concatenated HTML strings for styled KPIs
- NEVER use multi-line indented f-strings (Streamlit markdown parser treats 4+ space indent as code blocks, causing `</div>` to leak as visible text)
- This bug recurred across Projects 8, 9, 10. Do NOT revert to multi-line templates.

### Responsiveness

- Avoid blocking pipelines and long dead-screen waits
- Progressive loading where engines take time
- Every engine/data card shows explicit status: loading / success / failed / degraded
- Spinners with context ("Loading factor exposure..."), not generic "Please wait"

---

## 9. LLM integration

- **Default:** ON when ANTHROPIC_API_KEY environment variable is present. If no key is present or the call fails, the app remains fully operational in deterministic mode.
- **Provider:** Claude API (anthropic SDK)
- **Usage:** Research workspace only (Phase 4 memo synthesis)
- **Invariant:** LLM receives the deterministic recommendation in its prompt. LLM cannot override the rating. If LLM output contradicts the deterministic rating, flag the inconsistency.
- **Failure handling:** If LLM call fails or key is absent, the Research workspace works fully with Phases 1-3. Memo section shows "LLM synthesis unavailable" as appropriate. Never crash or block on LLM failure.
- **Scenario integration:** P&L engine provides structured bull/base/bear payoffs as LLM input context.

---

## 10. Deployment

### Primary: Paid hosted container environment

This terminal is designed to run as a live, always-on website on a hosted container platform or cloud VM (Railway, Render, Fly.io, AWS ECS, or equivalent).

Streamlit Community Cloud is NOT a target for the real application and must not influence architecture decisions. A lightweight showcase deployment may exist separately, but the core app is built for always-on hosted deployment.

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app/app.py", "--server.port=8501", "--server.headless=true"]
```

### Environment variables

```
FMP_API_KEY         # REQUIRED for production (single-stock market data)
FINNHUB_API_KEY     # Ticker-specific news (optional; falls back to yfinance)
ANTHROPIC_API_KEY   # LLM memo synthesis (enabled automatically when present)
FRED_API_KEY        # REQUIRED for macro data
APP_MODE            # "production" or "development" (default: production)
```

### Mode behavior

- **production** (default): FMP + FRED. No yfinance. LLM on if key present. SQLite persistence.
- **development**: yfinance allowed (with visible DEV MODE banner). JSON watchlist fallback. LLM optional.

---

## 11. Config rules

- config.yaml drives everything
- No decorative config keys. Every key must be consumed by code.
- No hardcoded thresholds, weights, or assumptions outside config unless absolutely structural
- Config must stay truthful: write tests that mutate config values and verify output changes

---

## 12. Testing strategy

- Unit tests for every adapter (mock the vendored kernel, test I/O schema)
- Unit tests for every engine (pnl, recommendation, regime, breadth)
- Unit tests for data layer (mock provider responses, test schema normalization)
- Unit tests for managers (cache behavior, TTL expiry, config-hash invalidation)
- Integration test: full Research pipeline on synthetic data
- Integration test: Portfolio build-decompose-validate workflow on synthetic data
- Config truthfulness tests: mutate config, verify output changes

---

## 13. Known bugs to prevent (lessons from Projects 8-10)

1. Plotly chart titles showing "undefined": every chart needs an explicit string title
2. Streamlit import errors: use **absolute** imports (`from app.X import ...`) AND a `sys.path` bootstrap in every entry-point file. `streamlit run app/app.py` loads the file as a top-level script, NOT as `app.app`, so relative imports crash with `attempted relative import with no known parent package`. This bit us on the first Railway deploy. Same applies to every page in `app/pages/` because `st.Page("pages/X.py")` also loads each page as a script.
3. Dividend yield bug: use `trailingAnnualDividendRate / spot`, not `dividendYield`. Warn if q > 0.15
4. yfinance rate scaling: Treasury yields come as percentages, divide by 100
5. Circular validation: do not extract IV then reprice with same IV and call it validation
6. Solver success checks: always check `result.success` from scipy. Fallback on failure
7. Interpretation callouts: every chart gets one. Observation / interpretation / implication format
8. Framing: never claim alpha generation. Frame as "understanding the instrument"
9. Units everywhere: all chart axes must have explicit units
10. Model limitations visible: show assumptions and limitations in sidebar or header
11. styled_kpi HTML bug: single-line concatenated strings ONLY. No multi-line f-strings.
12. Cache serialization: use pickle for cache, not JSON (JSON silently corrupts DataFrames via `default=str`)
13. LLM independence: app must work fully with LLM off
14. Deterministic before narrative: scores computed before LLM sees data
15. Config truthfulness: test that config changes propagate to output

---

## 14. Simplifying assumptions

- v1 uses 2 of 4 portfolio optimizers (MV + HRP). Risk Parity and Black-Litterman are documented future upgrades.
- v1 does not include delta hedging simulation from P9 (full options lab is sufficient).
- v1 does not include full M&A database rebuild, only query interface for comps.
- v1 does not include full factor backtest UI, only snapshot exposure.
- v1 does not include TSMOM full backtest, only signal snapshot.
- LBO Quick Calc is base case only, not full scenario lab with Monte Carlo.
- Market breadth is computed from a configurable universe (default: S&P 500 proxy via sector ETFs), not individual stock-level breadth.
- Polygon.io provider is interface-ready but not wired in v1. Migration requires config change + API key only.
- FMP options chain coverage may be limited for some tickers. Degrade gracefully with explicit messaging.

---

## 15. Dependencies

```
pandas
numpy
numpy-financial
# FMP is accessed via plain requests; no SDK package needed.
yfinance                  # LOCAL DEVELOPMENT ONLY
fredapi                   # FRED macro data (required in all modes)
pyyaml
streamlit
plotly
scipy
anthropic                 # LLM memo synthesis (auto-enabled when key present)
pytest
requests
```

---

## 16. Cross-project reuse map

| Adapter | Source project | Vendored kernel |
|---------|--------------|-----------------|
| research_adapter | P10: AI Research Agent | orchestrator.run_pipeline |
| lbo_adapter | P1: LBO Engine | lbo core engine (base case) |
| pe_scoring_adapter | P2: PE Target Screener | percentile scoring + valuation |
| factor_adapter | P3: Factor Backtest Engine | factor computation snapshot |
| ma_comps_adapter | P4: M&A Database | deal queries + regime classification |
| regime_adapter | P5: Volatility Regime Engine | composite regime detection (rule-based) |
| tsmom_adapter | P6: TSMOM Engine | signal computation snapshot |
| robustness_adapter | P7: Strategy Robustness Lab | PBO + DSR + plateau detection |
| optimizer_adapter | P8: Portfolio Optimization | MV + HRP optimizers |
| options_adapter | P9: Options Pricing Engine | BS Greeks, IV extraction, vol surface |

---

*CLAUDE.md -- Mini Bloomberg Terminal (Project 11)*
*Written: 2026-04-10, updated 2026-04-12*
*Status: COMPLETE. v1.3.0 shipped 2026-04-12. 137 tests passing. Production stack: Railway + Cloudflare + FMP + FRED + Finnhub + Anthropic + SQLite. See "v1.3 changes" section above for full changelog.*
