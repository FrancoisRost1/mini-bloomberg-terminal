# CLAUDE.md -- Mini Bloomberg Terminal (Project 11 of 11)

> Read this file fully before writing any code. This is the single source of truth for Project 11.
> This is the FINAL BOSS project: a unified investment research terminal integrating all 10 prior projects.

---

## Commands

```
# Run the app locally (development mode)
APP_MODE=development streamlit run app/app.py

# Run the app in production mode (requires ALPHA_VANTAGE_API_KEY + FRED_API_KEY)
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
- Production provider is Alpha Vantage (`terminal/data/provider_alphavantage.py`) with auto-fallback from `TIME_SERIES_DAILY_ADJUSTED` (paid) to `TIME_SERIES_DAILY` (free) via `PremiumEndpointError`. yfinance is dev-only. Mode enforcement lives in `terminal/data/provider_registry.py`.
- All config flows through `terminal/config_loader.py`; PE scoring bands and regime thresholds live in `config.yaml`. Every consumed key has a config-truthfulness test.
- File size limit: ~150 lines per Python module. Split proactively.
- Production stack: Railway (hosting) + Cloudflare (DNS) + Alpha Vantage (market data) + FRED (macro) + Anthropic (LLM) + SQLite (persistence). Streamlit Community Cloud is irrelevant.

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
- **Cold-render Alpha Vantage budget optimization**: Market Overview can exceed the free-tier rate limit on a single render. Mitigation requires either pre-warming on boot or accepting a paid-tier requirement.

---

## 0. Live-first operating rule

This application is intended to run as an always-on hosted website, not a classroom demo.

Every infrastructure, provider, caching, and persistence decision must optimize for reliability and real usage, not for free-tier convenience.

Hard rules:
- The production path uses Alpha Vantage as the primary market data provider. yfinance is allowed only for local development. No silent fallback to yfinance in production.
- If the primary provider is unavailable, the app must show an explicit DEGRADED or DATA UNAVAILABLE state. It must never silently serve stale or unofficial data without labeling it.
- LLM synthesis is enabled by default when ANTHROPIC_API_KEY is present. The app still works fully without it, but the intended live deployment includes continuous LLM availability.
- Persistence uses SQLite for the hosted app. JSON fallback is allowed only for local development.
- The real deployment target is a paid hosted container environment (cloud VM, Railway, Render, etc.). Streamlit Community Cloud is not a target for the real application and must not influence architecture decisions.
- Cache aggressively. The terminal must stay cheap and responsive on low-tier API plans (Alpha Vantage 25 req/min is more than enough for single-user usage).
Production stack: Railway (hosting) + Cloudflare (domain/DNS) + Alpha Vantage (market data) + FRED (macro) + Anthropic (LLM) + SQLite (persistence). Streamlit Community Cloud is irrelevant.

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
    style_inject.py                 # Bloomberg dark mode CSS
    header.py                       # global header component (ticker bar, watchlist, market strip)
    pages/
      __init__.py
      market_overview.py            # MARKET workspace
      ticker_deep_dive.py           # RESEARCH workspace
      options_lab.py                # ANALYTICS: Options Lab
      lbo_quick_calc.py             # ANALYTICS: LBO Quick Calc
      comps_relative_value.py       # ANALYTICS: Comps & Relative Value
      portfolio_builder.py          # PORTFOLIO workspace
  terminal/
    __init__.py
    config_loader.py                # load config.yaml once, pass as dict
    data/
      __init__.py
      provider_interface.py         # MarketDataProvider ABC
      provider_alphavantage.py      # Alpha Vantage: PRODUCTION provider (fully implemented)
      provider_yfinance.py          # yfinance: LOCAL DEV ONLY (excluded from production config)
      provider_polygon.py           # Polygon.io: future upgrade stub (interface-ready, not wired)
      provider_fred.py              # FRED API for macro data (always used, not a fallback)
      provider_registry.py          # provider selection, mode enforcement (dev vs production), no silent fallback
      schemas.py                    # normalized dataclasses: PriceData, Fundamentals, MacroData, OptionsChain
      cache.py                      # cache layer with config-hash keys, aggressive TTLs
    managers/
      __init__.py
      data_manager.py               # SharedDataManager (st.cache_resource)
      analytics_manager.py          # AnalyticsManager (st.cache_data for expensive engine outputs)
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
- All imports inside `app/` use relative imports. `app/` contains `__init__.py`.
- Never use absolute package imports like `from app.module import ...`.

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
# - production mode: Alpha Vantage only. If unavailable, DEGRADED state. No silent yfinance fallback.
# - development mode: yfinance allowed, with visible DEV MODE indicator.
# - FRED is always used for macro in both modes.
# - Architecture preserves easy swap to Polygon: change config provider key + add API key.
```

### Provider implementations

1. **provider_alphavantage.py**: PRODUCTION provider. Fully implemented Alpha Vantage integration using their documented REST API. Covers: daily/intraday prices, company fundamentals (income statement, balance sheet, cash flow), key ratios, and options chain. API key loaded from ALPHA_VANTAGE_API_KEY env var. Rate limit: 75 requests/minute on paid tier. Must handle rate limiting with exponential backoff. All responses normalized into terminal schemas. This is NOT a stub. It must be fully implemented in Phase 2 (Scaffold).
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
ALPHA_VANTAGE_API_KEY   # REQUIRED for production (market data)
ANTHROPIC_API_KEY       # LLM memo synthesis (enabled automatically when present)
FRED_API_KEY            # REQUIRED for macro data
APP_MODE                # "production" or "development" (default: production)
```

### Mode behavior

- **production** (default): Alpha Vantage + FRED. No yfinance. LLM on if key present. SQLite persistence.
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
2. Streamlit import errors: use relative imports + `__init__.py` in `app/`
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
- Alpha Vantage options chain coverage may be limited for some tickers. Degrade gracefully with explicit messaging.

---

## 15. Dependencies

```
pandas
numpy
numpy-financial
alpha_vantage             # PRODUCTION market data provider
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
*Written: 2026-04-10*
*Status: SPEC LOCKED, ready for Phase 2 (Scaffold)*
