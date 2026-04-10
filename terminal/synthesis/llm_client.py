"""Anthropic LLM client for Research workspace memo synthesis.

Invariants enforced here:
1. The deterministic recommendation is computed BEFORE this module is
   ever called. The rating is passed in as an immutable input string.
2. The system prompt forbids the LLM from changing the rating, and the
   parser flags any inconsistency.
3. Every failure path returns a structured ``skipped`` dict; this
   function NEVER raises. The Research page must remain fully functional
   when the LLM is unavailable.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any


SYSTEM_PROMPT = """You are an investment analyst writing a research memo.
You will be given a deterministic recommendation already computed by a
quantitative pipeline. You MUST NOT change the rating, the composite
score, or any sub-score. Your job is to write the narrative around them.

Constraints:
- The rating field in your output must equal the rating you were given.
- Do not invent financial metrics. Only use the values provided.
- Each section must be 2-4 sentences. No headings beyond the section names.
- Format: thesis | valuation | quality | momentum | risk | conclusion.
- Output sections in order, separated by blank lines, with the section
  name on its own line followed by the prose.
"""


def is_available() -> bool:
    """LLM is available iff the SDK imports AND the API key is set."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return False
    try:
        import anthropic  # noqa: F401
        return True
    except ImportError:
        return False


def generate_memo(
    ticker: str,
    recommendation: dict[str, Any],
    ratios: dict[str, float],
    scenarios: list[dict[str, Any]],
    llm_cfg: dict[str, Any],
) -> dict[str, Any]:
    """Synthesize a research memo via the Anthropic API.

    Returns a dict with ``status`` (``"success"`` or ``"skipped"``),
    ``memo`` (markdown text or None), ``rating_locked`` (the rating
    that was passed in), and ``inconsistency`` (None if the LLM didn't
    try to override the rating, else a description of the contradiction).
    """
    if not is_available():
        return _skipped("ANTHROPIC_API_KEY not set or anthropic SDK missing")
    try:
        import anthropic
    except ImportError:
        return _skipped("anthropic SDK not installed")

    rating = str(recommendation.get("rating", "INSUFFICIENT_DATA"))
    composite = recommendation.get("composite_score")
    sub_scores = recommendation.get("sub_scores", {})

    user_prompt = _build_user_prompt(ticker, rating, composite, sub_scores, ratios, scenarios)

    try:
        client = anthropic.Anthropic()
        message = client.messages.create(
            model=str(llm_cfg.get("model", "claude-sonnet-4-20250514")),
            max_tokens=int(llm_cfg.get("max_tokens", 4000)),
            temperature=float(llm_cfg.get("temperature", 0.3)),
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except Exception as exc:
        return _skipped(f"anthropic API call failed: {exc}")

    try:
        text = message.content[0].text
    except (IndexError, AttributeError) as exc:
        return _skipped(f"anthropic response had no text content: {exc}")

    inconsistency = _detect_rating_override(text, rating)
    return {
        "status": "success",
        "memo": text,
        "rating_locked": rating,
        "inconsistency": inconsistency,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def _build_user_prompt(
    ticker: str,
    rating: str,
    composite: float | None,
    sub_scores: dict[str, float],
    ratios: dict[str, float],
    scenarios: list[dict[str, Any]],
) -> str:
    lines = [
        f"Ticker: {ticker}",
        f"Rating: {rating} (LOCKED -- DO NOT OVERRIDE)",
        f"Composite score: {composite:.1f}" if composite == composite else "Composite score: n/a",
        "",
        "Sub-scores:",
    ]
    for key, val in sub_scores.items():
        lines.append(f"  {key}: {val:.1f}" if val == val else f"  {key}: n/a")
    lines.append("")
    lines.append("Key ratios:")
    for key, val in ratios.items():
        if isinstance(val, (int, float)) and val == val:
            lines.append(f"  {key}: {val:.4f}")
    lines.append("")
    lines.append("Scenario payoffs:")
    for s in scenarios:
        lines.append(f"  {s['scenario']}: target ${s['price_target']:.2f}, P&L ${s['dollar_pnl']:+.2f}")
    lines.append("")
    lines.append("Write the six-section memo now. Remember: rating is locked.")
    return "\n".join(lines)


def _detect_rating_override(memo_text: str, rating: str) -> str | None:
    """Flag if the LLM mentions a rating that contradicts the locked one."""
    other_ratings = {"BUY", "HOLD", "SELL", "INSUFFICIENT_DATA"} - {rating}
    upper = memo_text.upper()
    for other in other_ratings:
        if other in upper and rating not in upper:
            return f"LLM mentioned rating '{other}' but locked rating is '{rating}'"
    return None


def _skipped(reason: str) -> dict[str, Any]:
    return {
        "status": "skipped", "memo": None, "rating_locked": None,
        "inconsistency": None, "reason": reason, "generated_at": None,
    }
