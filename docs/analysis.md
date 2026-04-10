# analysis.md -- Mini Bloomberg Terminal (Project 11)

## 1. What this terminal is an investment view on

The Mini Bloomberg Terminal is not a single-name pitch. It is an opinionated integration of ten standalone engines into one research workstation, and the thesis below is about the *terminal itself* as a product: what it says about how to do investment research, which decisions it is built to make defensible, and where its edges and blind spots live.

The terminal answers four investor questions in one tool:

1. **Market**: What regime are we in? (rule-based composite over trend, vol, drawdown, credit)
2. **Research**: Should I own this? (deterministic composite score with a non-negotiable LLM override barrier)
3. **Analytics**: What is the instrument math? (LBO returns, Greeks, peer comps)
4. **Portfolio**: How should I allocate, and is the allocation stable? (MV + HRP build, factor decompose, PBO/DSR/plateau validate)

The product-level thesis is that an analyst should never have to switch between a pricing tool, a screener, a regime monitor, and a robustness lab to reach a decision. Fragmented tooling is how hidden assumptions accumulate. A unified terminal with a single data layer, a shared config, and a deterministic recommendation path makes the chain of reasoning auditable.

---

## 2. Investment thesis

**Core claim:** Deterministic analytics compounded with disciplined data hygiene produce better decisions than any single exotic model. The terminal operationalises this claim in three ways:

1. **Data plumbing is treated as a production problem, not a notebook concern.** Alpha Vantage is the live-first production provider. yfinance exists only as a development fallback and is refused at the mode boundary in production. This is encoded in `provider_registry.py` and guarded by `tests/test_data/test_provider_registry.py`. The belief: research conclusions built on scraped data without SLA are lower in quality than the same conclusions built on paid API data, even when the numbers look the same.

2. **The LLM is an interpreter, not a decision maker.** The Research pipeline computes the deterministic recommendation before the LLM is ever called. The LLM receives the rating as an immutable input in its prompt and is forbidden from overriding it. If the LLM output contradicts the deterministic rating, the inconsistency is flagged. The belief: narrative coherence without deterministic grounding is a failure mode specific to LLM-augmented research, and the guardrail must be architectural, not aspirational.

3. **Every optimisation is validated before it is trusted.** The Portfolio workspace ties PBO, deflated Sharpe, and plateau fraction directly to the selected portfolio, not to an abstract detached lab. The belief: a backtest without robustness validation is overfit with probability you cannot quantify. Showing the validation next to the weights is the only way to keep it honest.

**What the terminal is NOT a view on:** no individual stock, no macro forecast, no alpha claim. Framing matters -- this product is about understanding instruments and portfolios, not generating alpha. Projects 3, 5, 6, 7, and 8 individually test real signals; this project integrates them into an interpretation layer.

---

## 3. Key risks

**Data layer risks**

- **Alpha Vantage outage or rate-limit surge.** Free tier is 25 req/min, paid is 75 req/min. The terminal caches aggressively (5 minutes for prices, 1 hour for fundamentals) and uses exponential backoff on rate-limit responses. If Alpha Vantage is down, production mode surfaces DEGRADED badges rather than silently falling back to yfinance. Mitigated by `provider_registry.py` mode enforcement and the degraded-state rendering in `utils/error_handling.py`.
- **Stale data masquerading as live data.** Caching can hide staleness. Mitigated by visible TTLs in the header, the `snapshot_age()` timestamp on the SharedDataManager, and the fact that cache keys embed the config hash so config changes invalidate automatically.
- **Alpha Vantage options chain coverage.** Not every ticker has a live HISTORICAL_OPTIONS response. Mitigated by the Options Lab explicitly rendering a DATA UNAVAILABLE card rather than crashing when the chain is empty.
- **Dividend yield field.** The yfinance `dividendYield` field is unreliable; the yfinance provider uses `trailingAnnualDividendRate / spot` and warns when q exceeds the configured threshold.

**Model risks**

- **LBO Quick Calc is base case only.** No Monte Carlo, no covenant breach detection, no working capital seasonality. The sidebar states this explicitly. A narrow base case is useful for pricing the return mechanics; it is not a full deal model.
- **Options Lab uses European Black-Scholes and a Taylor-expansion P&L scenario.** No American early exercise, no delta hedging simulation, no full reprice in the scenario grid. These are flagged in the sidebar. For any real position sizing decision, a full repricing engine is required.
- **Regime classifier is rule-based, not HMM-trained.** The rules are stable and interpretable but they can lag sudden regime transitions. Confidence is reported alongside the label so consumers do not treat it as binary.
- **Portfolio optimiser is MV + HRP only.** Risk Parity and Black-Litterman are listed as future upgrades but absent in v1. For users who want Bayesian view blending, the current tool is insufficient.
- **Robustness trial matrix is simple in v1.** The portfolio workflow generates a small perturbation-based trial matrix to feed PBO/DSR rather than running a full parameter grid. This is enough for directional verdicts but less rigorous than a full CSCV over a real parameter space. The P7 full pipeline remains available as a standalone engine.

**Implementation risks**

- **Streamlit rendering pitfalls recur.** The project carries a list of fifteen known bugs from Projects 8-10 (multi-line f-string HTML bleed, plotly chart titles showing "undefined", missing axis units). The codebase uses single-line styled KPIs and a chart helper module to prevent them. Regression is possible if helpers are bypassed.
- **LLM cost drift.** Anthropic API usage is metered. The terminal enables LLM synthesis only on the Research workspace and only when the key is present. A production deployment with heavy traffic should rate-limit LLM calls externally.

---

## 4. Valuation assumptions (terminal as a product)

When a terminal is the product, valuation is about the cost-to-value ratio of running it, not a DCF.

**Build cost:** Ten prior engines were built standalone. This project integrates them, which is roughly 20 to 30 percent of the cost of building them from scratch because the analytical core is already validated and audited. The integration cost lives almost entirely in the data layer (provider, cache, schemas) and the UI orchestration.

**Running cost in production:**

- Alpha Vantage paid tier: ~USD 50/month for 75 req/min and fundamentals coverage.
- FRED API: free (API key required).
- Anthropic API: variable, with caching on by default the per-session cost is small.
- Railway / Render container: ~USD 5 to 20/month for a small always-on instance.
- Cloudflare DNS and domain: small fixed annual cost.
- SQLite persistence: zero (filesystem on the container volume).

**Total:** ~USD 60 to 80/month for a fully live-first production deployment with continuous LLM availability. The comparison benchmark is a Bloomberg Terminal seat at ~USD 24,000/year. The value gap is not about feature parity (there is none) but about the cost of having a reproducible, auditable, self-hosted research environment that an analyst actually owns.

**Assumptions embedded in the terminal's default config:**

- Cache TTL: 5 min prices, 1 hour fundamentals, 30 min macro, 2 min options, 15 min engine results. Chosen for a single-user low-tier Alpha Vantage plan.
- Recommendation thresholds: BUY >= 65, SELL <= 35, HOLD between. From the P10 audit.
- Composite weights: valuation 35, quality 25, momentum 20, risk 20. These are opinionated: valuation carries the most weight because it is the most reproducible signal. Users can mutate weights in config.yaml and the test suite guarantees config changes propagate.
- Data gates: hard-fail on no prices or no financials. Degraded on missing filings. The Research workspace refuses to serve a number when the underlying data is missing.

---

## 5. Return scenarios (terminal as a decision tool)

For a terminal, "return" is the quality-of-decision uplift over using the prior fragmented toolchain. Three scenarios.

**Bull case: terminal is load-bearing.** The analyst uses the terminal daily. Deterministic recommendations are checked against LLM narratives and disagreements are investigated; the disagreement log itself becomes a research diary. Portfolio robustness verdicts are gating criteria for production allocations. Alpha Vantage is in production mode, caches are warm, LLM is always available. Decisions are auditable through the deterministic path, and the terminal pays for itself many times over in avoided bad trades.

**Base case: terminal is a research surface.** The analyst uses the terminal for Market Overview and Ticker Deep Dive primarily, with occasional trips into Options Lab and LBO Quick Calc. Portfolio workspace is used for ad hoc construction rather than production allocation. The terminal replaces half a dozen tabs and three spreadsheets. Marginal decision quality improves through faster iteration and consolidated state.

**Bear case: terminal is an interview artefact.** The live-first infrastructure is built and works, but day-to-day usage never materialises. The value then is the integration exercise itself: a demonstration that the analyst can design and ship production-grade research tooling. Still a useful deliverable, but the return is in what the project proves about the builder, not in what it produces daily.

**What would move from base to bull:**

1. Wire a second paid provider (Polygon) and use provider redundancy to stop treating data availability as a question.
2. Replace the perturbation trial matrix in Portfolio Phase 3 with a real parameter grid driven by the P7 connector.
3. Add a decision log page that persists every deterministic recommendation with the rule trace, so the LLM cannot slide into the decision history after the fact.
4. Build a scheduled job that runs the Research pipeline against the watchlist nightly and writes a markdown digest.

---

## 6. What I would change in v2

In rough priority order:

1. Replace the Alpha Vantage options chain coverage gap with a secondary options data source. Options are the page most likely to show DATA UNAVAILABLE.
2. Add an explicit decision log table (SQLite) alongside the watchlist. Every Research pipeline run writes the rating, composite score, rule trace, and LLM output if present. This is the single biggest upgrade to reproducibility.
3. Wire Black-Litterman and Risk Parity into the Portfolio workspace. BL in particular closes the gap between the LLM narrative on the Research page and the deterministic portfolio weights.
4. Make the regime classifier time-aware. The current rule composite has no memory; adding a 3-day persistence filter (as in P5 full) would reduce regime flicker.
5. Move caching from filesystem pickle to Redis on the Railway deployment, to support multi-replica scaling if usage grows.

---

## 7. Positioning

The terminal's posture is deliberate: understand the instrument, respect the data layer, make the deterministic path auditable, let the LLM narrate but never decide. That is the position the product takes, and every architectural choice in Phase 2 was made to defend it.

The terminal does not claim to generate alpha. It claims to make research reproducible, decisions traceable, and tooling affordable. Those are more defensible claims and they are the claims a junior analyst should be making at an interview.
