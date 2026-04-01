"""Tests for strategist prompt construction."""

from __future__ import annotations

from unittest.mock import MagicMock

from trustdesk.strategist.prompts import (
    SYSTEM_PROMPT,
    build_regime_context,
    build_user_prompt,
)


class TestSystemPrompt:
    def test_system_prompt_contains_decision_types(self) -> None:
        assert "PROPOSE" in SYSTEM_PROMPT
        assert "PASS" in SYSTEM_PROMPT

    def test_system_prompt_contains_thresholds(self) -> None:
        assert "1.00" in SYSTEM_PROMPT
        assert "0.80" in SYSTEM_PROMPT
        assert "0.60" in SYSTEM_PROMPT
        assert "0.40" in SYSTEM_PROMPT

    def test_system_prompt_mentions_all_regimes(self) -> None:
        assert "TRENDING_UP" in SYSTEM_PROMPT
        assert "TRENDING_DOWN" in SYSTEM_PROMPT
        assert "RANGING" in SYSTEM_PROMPT
        assert "VOLATILE" in SYSTEM_PROMPT


class TestBuildRegimeContext:
    def test_trending_up(self) -> None:
        ctx = build_regime_context("TRENDING_UP")
        assert "pullback" in ctx.lower()
        assert "BTC" in ctx

    def test_trending_down(self) -> None:
        ctx = build_regime_context("TRENDING_DOWN")
        assert "PASS" in ctx
        assert "cash" in ctx.lower()

    def test_ranging(self) -> None:
        ctx = build_regime_context("RANGING")
        assert "Bollinger" in ctx

    def test_volatile(self) -> None:
        ctx = build_regime_context("VOLATILE")
        assert "50%" in ctx
        assert "STRONG" in ctx

    def test_unknown_regime_returns_caution(self) -> None:
        ctx = build_regime_context("UNKNOWN_REGIME")
        assert "UNKNOWN_REGIME" in ctx
        assert "caution" in ctx.lower()


class TestBuildUserPrompt:
    def test_user_prompt_contains_signal_data(self) -> None:
        signal = MagicMock()
        signal.regime = "TRENDING_UP"
        signal.model_dump.return_value = {
            "pair": "BTC/USD",
            "alignment_score": 0.85,
            "regime": "TRENDING_UP",
        }
        prompt = build_user_prompt(signal)
        assert "BTC/USD" in prompt
        assert "TRENDING_UP" in prompt
        assert "PROPOSE or PASS" in prompt

    def test_user_prompt_includes_regime_context(self) -> None:
        signal = MagicMock()
        signal.regime = "VOLATILE"
        signal.model_dump.return_value = {"pair": "ETH/USD"}
        prompt = build_user_prompt(signal)
        assert "VOLATILE" in prompt
        assert "50%" in prompt
