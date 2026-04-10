# Mini Bloomberg Terminal

Unified investment research workstation in Streamlit. Integrates ten standalone financial engines (LBO, PE screener, factor models, regime detection, TSMOM, options, portfolio optimisation, robustness lab, and an AI research agent) into a single Bloomberg-style terminal with four workspaces: Market, Research, Analytics, Portfolio.

Production stack: Railway (hosting) + Cloudflare (domain / DNS) + Alpha Vantage (market data) + FRED (macro) + Anthropic (LLM) + SQLite (persistence). Streamlit Community Cloud is not a target for this application.

## Why this exists

A focused, institutional-grade research terminal where an analyst can go from market overview to deep-dive research to portfolio construction without switching tools. Every analytical result is deterministic and traceable. The LLM layer is optional and never overrides deterministic ratings.

## Quick start

```bash
# 1. Install dependencies
pip3 install -r requirements.txt

# 2. Set environment variables
export ALPHA_VANTAGE_API_KEY=...   # REQUIRED in production
export FRED_API_KEY=...            # REQUIRED (macro)
export ANTHROPIC_API_KEY=...       # optional, auto-enables LLM memo
export APP_MODE=development        # "production" or "development"

# 3. Run the app
streamlit run app/app.py

# 4. Run the test suite
python3 -m pytest
```

See `.env.example` for the full list of environment variables.

## Modes

- **production** (default, what runs on Railway): Alpha Vantage + FRED. No yfinance. LLM on if `ANTHROPIC_API_KEY` present. SQLite persistence (`data/terminal.db`).
- **development**: yfinance allowed with a visible DEV MODE banner. JSON watchlist fallback. LLM optional.

The mode is enforced at `terminal/data/provider_registry.py`. Production mode will refuse to instantiate yfinance even if it is configured. This is guarded by `tests/test_data/test_provider_registry.py`.

## Architecture

```
app/                     # Streamlit UI
  app.py                 # entry point, st.navigation, global header
  header.py              # ticker bar, watchlist, market strip
  pages/                 # 6 workspace pages
terminal/                # business logic
  config_loader.py       # loads config.yaml once
  data/                  # providers, schemas, cache, registry
  managers/              # SharedDataManager, AnalyticsManager
  adapters/              # 10 adapters wrapping P1-P10 kernels
  engines/               # pnl, recommendation, regime, breadth
  utils/                 # formatting, charts, errors, watchlist IO
tests/                   # full offline test suite (no network calls)
```

Architecture details and per-module specs live in `CLAUDE.md` (the single source of truth for this project).

## Design rules

- One file, one responsibility. No module exceeds ~150 lines.
- All thresholds, weights, and assumptions live in `config.yaml`. No hardcoded numbers.
- All data flows through the `MarketDataProvider` interface. The UI never touches raw provider payloads.
- Every chart has an explicit string title, explicit axis units, and an observation / interpretation / implication callout.
- Styled KPIs are single-line HTML strings only (multi-line f-strings trigger a Streamlit markdown bug).
- The LLM receives the deterministic rating as an immutable prompt input and cannot override it.

## Deployment

Build the container and run it against your production env file:

```bash
docker build -t mini-bloomberg .
docker run -p 8501:8501 --env-file .env mini-bloomberg
```

On Railway: set the environment variables in the project settings, point Cloudflare DNS at the Railway-generated domain, and enable the Railway persistent volume if you want the SQLite watchlist to survive deploys.

## Investment write-up

See `docs/analysis.md` for the thesis, risks, valuation assumptions, and return scenarios for the terminal as a product.

## Related projects

The ten engines that feed the adapters live in sibling repositories:

- P1 LBO Engine, P2 PE Target Screener, P3 Factor Backtest Engine
- P4 M&A Database, P5 Volatility Regime Engine, P6 TSMOM Engine
- P7 Strategy Robustness Lab, P8 Portfolio Optimization Engine
- P9 Options Pricing Engine, P10 AI Research Agent

See the parent `CODE/CLAUDE.md` for the full index and cross-project reuse map.
