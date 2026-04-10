# Mini Bloomberg Terminal — Handover v2

Snapshot of the state of Project 11 after three consecutive polish
sessions (the v3 prompt session, the regression bug fix session, and
the final density / data quality session). Tests: **137 passing**.
Branch: `main`. Deployment target unchanged: Railway + Cloudflare +
FMP + FRED + yfinance + Anthropic + SQLite.

This file is the single source of truth for "what shipped since the
v1 cut". The root `CLAUDE.md` and `mini-bloomberg-terminal/CLAUDE.md`
describe the architecture and invariants; this file is a chronology.


## Session 1 — v3 polish (commit `5038d20`)

Priorities were delivered top-down; 137 tests green at the end.

### Priority 1 — data quality
- **Interest coverage KPI**: `compute_ratios` in `_fmp_ratios.py` now
  always seeds `interest_coverage` in the ratios dict and attaches a
  `_notes` companion dict. New `fmt_ratio_with_note` formatter in
  `terminal/utils/formatting.py` reads the note and displays a short
  sentinel ("N/R" after the Session 2 shortening) instead of a bare
  `n/a` when FMP does not disclose `interestExpense`.
- **Research P/E n/a root cause**: the outer try/except in
  `ticker_deep_dive.render` was catching every downstream pipeline
  exception and returning a bare `hard_failure` packet with no
  `fundamentals` key. Phase 1 KPIs therefore all rendered `n/a` even
  when FMP data was fine. Fix: fetch `raw_prices` and `raw_fundamentals`
  directly from `SharedDataManager` before the pipeline call, then
  inject them into the packet via `setdefault` so Phase 1 always has
  data even when Phase 2/3 fail.
- **Regime classifier showing all zeros**: the engine returns
  `{-1, 0, +1}` scores per signal and NEUTRAL is the modal state, so
  the bar chart reads as "engine broken". Extracted `render_regime`
  into `app/pages/_market_regime.py`. The decomposition chart now
  shows raw magnitudes vs the configured stress thresholds (trend %,
  vol vs stress %, drawdown %, HY vs stress %) and the side table has
  a three-column "Signal / Raw / Score" layout. Engine itself is
  untouched so existing regime tests still pass.

### Priority 2 — density and layout
- Sector breadth table: new columns `1D %`, `1W %`, `1M %`, `YTD %`,
  `1Y %`, `60D Trend`, all computed from the existing 1y fetch via
  `_pct_change_bars` and `_ytd_pct` helpers.
- Sector treemap sized by fund AUM via a `SECTOR_ETF_AUM_USD_BN`
  constant in `_market_heatmap.py` (XLK 72B down to XLRE 7B). The
  `sector_treemap` helper in `chart_helpers.py` gained an optional
  `sizes=` argument.
- Global density CSS pass in `app/density_css.py`: block-container
  padding, `stVerticalBlock` gap, `stHorizontalBlock` gap, `hr` margin,
  dataframe row padding, plotly chart padding, `h1`/`h3` margins, and
  the freshness footer all tightened 30-40%.

### Priority 3 — portfolio builder
- Removed the redundant per-method weight bar charts (donuts already
  show the allocation).
- New `render_drawdown_chart` in `app/pages/_portfolio_attribution.py`
  shows NAV drawdown paths for MV, HRP, and Equal Weight with max-dd
  labels in the title.
- New `render_risk_contributions` helper: computes
  `RC_i = w_i · (Σw)_i / (w'Σw)` for MV / HRP / EW and displays them
  side-by-side in a coloured dataframe. Each column sums to 100%.
- Split into three files to avoid a circular import:
  - `_portfolio_helpers.py` owns backtest + correlation
  - `_portfolio_attribution.py` owns drawdown + risk contributions
  - `_portfolio_common.py` owns the shared palette + series builder

### Priority 4 — comps completion
- Copied `real_deals.csv` (90 rows) from `ma-database/data/raw/` into
  `mini-bloomberg-terminal/data/raw/ma_deals.csv` and whitelisted it
  in `.gitignore`.
- `_normalize_real_deals` in the adapter remaps the P4 schema
  (`target_name`, `acquirer_name`, `sector_name`, `ev_to_ebitda`,
  `enterprise_value` in USD millions, `announcement_date`,
  `acquirer_type`) onto the terminal's canonical columns and scales
  EV from millions to full USD.
- `query_sector_comps` projects to a display-only column subset and
  the Comps page formats EV in billions and EV/EBITDA with the `x`
  suffix.
- Peer fundamentals table appends a "Sector median" bottom row, with
  the row styled as a summary band (distinct background, italic,
  muted colour). Active ticker row highlighted.
- New "HISTORICAL RANGE" tab (`_comps_historical.py`) computes annual
  EV/EBITDA across the last five fiscal years from FMP statements +
  year-end close price and renders a 5Y low / median / high range bar
  with the current multiple marked plus its percentile.
- Split `comps_relative_value.py` into an orchestrator page + a new
  `_comps_renderers.py` module to stay under the 150-line budget.

### Priority 5 — research refinements
- `tv_chart.py` (TradingView lightweight-charts embed) now uses a
  custom `tickMarkFormatter` that renders "Mon YY" labels, plus a
  matching `localization.timeFormatter` for the crosshair.
- Volume MA(20) overlay: new line series scoped to the volume
  histogram's price scale.

### Priority 6 — options lab
- Scenario tab: numeric grid with Spot / Move / Option Value / P&L $ /
  P&L % at fixed ±5/10/20% spot moves.
- Full chain table: ATM row highlighted in the project accent, ITM
  side amber-tinted, numeric columns right-aligned in monospace via a
  per-row Styler. Extracted IV smile into `_options_iv_smile.py` so
  both files stay under the line budget.

### Priority 7 — polish
- PE Score table rounds to 1 decimal via Styler `.format`.
- Sidebar nav titles shortened so the 180px sidebar never truncates:
  Market / Research / Options / LBO / Comps / Portfolio. `url_path`
  values are stable so bookmarks still resolve.
- Defensive CSS hides any `stPageLink` rendered inside the main
  content area.


## Session 2 — v3 regression bug fixes (commit `29a8f75`)

Four regressions from Session 1, found on the first browser pass.

1. **`_ytd_pct` tz crash** on Market Overview. yfinance returned a
   `DatetimeIndex(tz='America/New_York')` and the slice compared it
   against a naive `pd.Timestamp(f"{year}-01-01")`, raising "Cannot
   compare tz-naive and tz-aware". Fix: normalize the index to
   tz-naive on a local copy before slicing.
2. **Plotly 8-digit hex in drawdown chart**. `render_drawdown_chart`
   passed `fillcolor = hex + "15"` (an `#RRGGBBAA` shorthand) which
   Plotly rejects. New `_hex_to_rgba(hex, alpha)` helper in
   `_portfolio_attribution.py` translates to `rgba(r,g,b,a)`.
3. **TradingView chart "Jan 70" dates**. `df.index.view("int64") //
   10**9` silently collapses to 0 on pandas 2.x when the DatetimeIndex
   is tz-aware. Replaced with per-row
   `int(pd.Timestamp(ts).timestamp())` after converting the index to
   UTC-naive. Stable in every pandas version.
4. **"NOT REPORTED" clipping** on the narrow Research KPI strip.
   Shortened the interest coverage sentinel to `N/R` in
   `compute_ratios` and removed the implicit uppercasing in
   `fmt_ratio_with_note` so display-ready strings flow through.


## Session 3 — density overhaul + misc data quality (commit `dbc774c`)

Main theme: the Streamlit view had tangible KPI overlap and the
Market Overview looked like a long vertical scroll instead of a
terminal. Seven items shipped plus the four bugs that preceded them.

### Density
- **`dense_kpi_row`** (in `terminal/utils/density.py`): every grid
  cell now has `min-width:0`, `overflow:hidden` on the wrapper,
  `text-overflow:ellipsis` on label/value/delta, `title` tooltips for
  the full text. Default `min_cell_px` bumped 100→110, gap 0.2→0.3rem.
  Tight call sites were individually bumped from the 85-95 range up to
  105-118.

### FX and commodities
- FX majors extended from 3 to 6 pairs: EURUSD, GBPUSD, USDJPY,
  USDCHF, AUDUSD, USDCAD (yfinance `CHF=X`, `AUDUSD=X`, `CAD=X`).
- New `render_commodities_row` helper with WTI (`CL=F`), Gold
  (`GC=F`), Silver (`SI=F`), Copper (`HG=F`), Nat Gas (`NG=F`).

### Market Overview grid layout
Five-row grid so the dashboard fits above the fold on a 1400px
viewport:
- Row 1: Global indices 60% | Regime classifier 40%
- Row 2: Rates table 50% | Yield curve 50%
- Row 3: FX 33% | Commodities 33% | Macro snapshot 33%
- Row 4: Sector heatmap full width
- Row 5: Breadth table 60% | Gainers/losers 40%

### Research period selector
- `render_phase1_chart` takes an optional `data_manager`. A new
  horizontal radio (1M / 3M / 6M / 1Y / 2Y / 5Y) refetches prices
  only for the chart view. The rest of the pipeline keeps using
  `research.default_price_period` from config.

### Comps active row highlight
- The target ticker row in the peer fundamentals table now uses a
  vivid `rgba(224,112,32,0.22)` fill with an orange top/bottom border
  and the accent colour on the text.

### Options Lab density
- Scenario panel: tighter chart (240px, narrower margins), shorter
  column labels (`Opt Val`, `P&L $`, `P&L %`), numeric columns
  explicitly right-aligned and mono via `Styler.set_properties`.

### File split hygiene (Session 3)
- `_market_extras.py` split into `_market_extras` (yield curve) +
  `_market_rows` (FX, commodities, gainers-losers).
- `_market_overview_helpers.py` split: the breadth pane and the
  tz-safe `_ytd_pct` live in `_market_breadth.py`, helpers keeps
  indices + rates only.


## Session 4 — final polish (current session)

### Bug fixes
- **B1 treemap tooltip raw float**. `sector_treemap` now uses
  `texttemplate="%{text}"` to pin the pre-formatted strings
  (`+0.39%`, `+$72B`) and a dedicated `hovertext` list with "1D +X.XX%"
  so the tile never falls back to rendering the raw value. Fixes the
  "0.38712...%" leak on small tiles.
- **B2 "None" in full chain table**. `pd.merge(how="outer")` was
  filling rows where one side had no entry with NaN, which pandas
  Styler rendered as the string "None". Every missing cell now goes
  through `fillna("-")` so the table reads cleanly. `_side_frame`
  also skips strikes where both bid and ask are missing on that side.
- **B3 M&A EV/EBITDA sparse coverage**. Raw source has `ev_to_ebitda`
  populated for 5 of 90 deals. The mapping was correct all along;
  what was missing was the user signal. `run_comps` now reports a
  coverage stat (`coverage["ev_ebitda"]`) and the Comps page caption
  adds "EV/EBITDA limited coverage (X% disclosed)" when below 50%.
- **B4 Valuation scatter with one dot**. `render_ev_growth_scatter`
  now fetches the same 5 sector peers (via `sector_peers.peers_for`)
  and plots every peer with real data. Active ticker is drawn in the
  accent colour at a larger size. Crosshairs = median of the peers
  actually on screen.

### KPI overlap rounds (items 5-10)
- New `dense_kpi_rows` helper (plural) in `terminal/utils/density.py`
  that splits a long item list into N balanced rows. Rule: if a row
  has more than ~6 wide-label cells, split into two.
- Research Phase 1 KPI strip (11 cells): split into 2 rows of 6 and 5
  with `dense_kpi_rows(..., rows=2, min_cell_px=125)`.
- Research PE engine tab (up to 10 cells): split into 2 rows.
- Research deterministic rating strip (7 cells): split into 2 rows.
- LBO Quick Calc summary strip (11 cells): split into 2 rows of 6 and
  5 (entry side on top, exit side + returns on bottom).
- Portfolio MV / HRP method pane (6 cells): single row with
  `min_cell_px=125`.
- Portfolio concentration strip (6 cells): bumped to `min_cell_px=120`.
- Sweep of every other call site: anything under 115 bumped to 118 or
  120 so no row clips its labels on a 1400px viewport.

### Additional polish
- Options full chain filters out strikes where both sides are empty
  and sorts by strike.
- Comps sector median row relabelled `MEDIAN` with a heavier top
  border so it reads as a summary band, not a ticker.
- This handover document created at `project11_handover_v2.md`.


## Currently deferred / still open

### Deferred to v2 (explicit, pre-existing)
- Portfolio Phase 3 robustness validation. The adapter is standalone;
  needs a real CSCV parameter sweep, not weight perturbations.
- Risk Parity + Black-Litterman optimizers.
- Cold-render FMP budget optimisation on Market Overview.

### Known sharp edges not yet addressed
- `portfolio_builder.py` (156 lines), `_comps_historical.py` (151),
  `_comps_charts.py` (166), `terminal/data/_fmp_ratios.py` (~157),
  and `chart_helpers.py` (182) all sit slightly over the 150-line
  soft budget. Each is a cohesive single-purpose module; splitting
  would hurt more than help. Revisit only if they grow further.
- The TradingView candlestick embed is an iframe `st.components.html`
  call and therefore does not inherit the Streamlit dark CSS; future
  polish could push the chart into a Plotly `go.Candlestick` to share
  the theme, at the cost of losing MA50/MA200/volume overlays.
- Streamlit Cloud is NOT a target for this project; the hosted
  production path is Railway + Cloudflare and the audit should be
  re-run against that container rather than a local dev server.


## Cross-project reuse status

Every adapter from the 10 prior projects (LBO, PE scoring, Factor,
Regime, TSMOM, Options Greeks + IV, MV/HRP optimizer, Robustness PBO,
M&A comps, Research orchestrator) is wired through
`terminal/adapters/*.py` and consumed via `SharedDataManager`. No
page touches raw provider payloads; every call goes through the
normalized `PriceData`, `Fundamentals`, `MacroData`, `OptionsChain`
schemas. The single-stock route goes to FMP, index/ETF/options/FX
routes go to yfinance (production), macro goes to FRED. This is the
per-purpose routing invariant documented in
`mini-bloomberg-terminal/CLAUDE.md` Section 0.


## Test suite

```
python3 -m pytest
```

Expected: **137 passed, 1 warning** (urllib3/OpenSSL notice, not
actionable). The two regression tests added in Session 1 cover the
`_normalize_real_deals` schema mapping and the display column
projection for `query_sector_comps`.
