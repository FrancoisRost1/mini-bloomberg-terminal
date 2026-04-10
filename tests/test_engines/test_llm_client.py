"""Unit tests for the LLM memo client.

Fully offline. No network calls. The Anthropic SDK may not be importable
in the test env, in which case ``is_available`` returns False and
``generate_memo`` returns a structured skipped dict.
"""

from __future__ import annotations

from terminal.synthesis.llm_client import (
    _build_user_prompt,
    _detect_rating_override,
    generate_memo,
    is_available,
)


def test_generate_memo_skipped_when_no_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = generate_memo(
        ticker="AAPL",
        recommendation={"rating": "BUY", "composite_score": 75, "sub_scores": {}},
        ratios={},
        scenarios=[],
        llm_cfg={"model": "claude-sonnet-4-20250514", "max_tokens": 100, "temperature": 0.3},
    )
    assert result["status"] == "skipped"
    assert "ANTHROPIC_API_KEY" in result["reason"] or "anthropic" in result["reason"].lower()


def test_is_available_false_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert is_available() is False


def test_detect_rating_override_flags_contradiction():
    memo = "The stock should be rated SELL given the weakness in margins."
    flag = _detect_rating_override(memo, rating="BUY")
    assert flag is not None
    assert "SELL" in flag and "BUY" in flag


def test_detect_rating_override_no_false_positive():
    memo = "The composite scores support a BUY rating across all four sub-scores."
    assert _detect_rating_override(memo, rating="BUY") is None


def test_user_prompt_includes_locked_rating():
    prompt = _build_user_prompt(
        ticker="MSFT",
        rating="HOLD",
        composite=55.2,
        sub_scores={"valuation": 50.0, "quality": 70.0},
        ratios={"pe_ratio": 28.0, "ebitda_margin": 0.45},
        scenarios=[{"scenario": "bull", "price_target": 400, "dollar_pnl": 5000}],
    )
    assert "MSFT" in prompt
    assert "HOLD (LOCKED" in prompt
    assert "valuation: 50.0" in prompt
    assert "pe_ratio: 28.0000" in prompt
    assert "bull" in prompt
