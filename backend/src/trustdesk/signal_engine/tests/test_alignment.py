"""Tests for signal alignment scoring."""

from __future__ import annotations

import pytest

from trustdesk.schemas.signal_payload import Alignment
from trustdesk.signal_engine.alignment import (
    compute_alignment,
    compute_derived_values,
    compute_position_size,
    compute_stop_distance,
)
from trustdesk.signal_engine.regime import Regime
from trustdesk.signal_engine.types import CrossoverState, OBVTrend


class TestComputeAlignment:
    """Alignment score computation."""

    def test_strong_alignment(self) -> None:
        result = compute_alignment(
            crossover=CrossoverState.BULLISH,
            adx=30.0,
            volume_multiplier=1.5,
            obv_trend=OBVTrend.RISING,
            book_imbalance=0.65,
        )
        assert result.score == pytest.approx(1.0)
        assert result.grade == Alignment.STRONG

    def test_moderate_alignment(self) -> None:
        result = compute_alignment(
            crossover=CrossoverState.BULLISH,
            adx=30.0,
            volume_multiplier=1.5,
            obv_trend=OBVTrend.RISING,
            book_imbalance=0.45,
        )
        assert result.score == pytest.approx(0.8)
        assert result.grade == Alignment.MODERATE

    def test_weak_alignment(self) -> None:
        result = compute_alignment(
            crossover=CrossoverState.BULLISH,
            adx=30.0,
            volume_multiplier=0.8,
            obv_trend=OBVTrend.FALLING,
            book_imbalance=0.45,
        )
        assert result.score == pytest.approx(0.4)
        assert result.grade == Alignment.NO_SIGNAL

    def test_no_signal(self) -> None:
        result = compute_alignment(
            crossover=CrossoverState.BEARISH,
            adx=22.0,
            volume_multiplier=0.8,
            obv_trend=OBVTrend.FALLING,
            book_imbalance=0.45,
        )
        assert result.score <= 0.4
        assert result.grade == Alignment.NO_SIGNAL

    def test_three_of_five(self) -> None:
        result = compute_alignment(
            crossover=CrossoverState.BULLISH,
            adx=30.0,
            volume_multiplier=1.5,
            obv_trend=OBVTrend.FALLING,
            book_imbalance=0.45,
        )
        assert result.score == pytest.approx(0.6)
        assert result.grade == Alignment.WEAK


class TestAlignmentBreakdown:
    """Individual signal contributions."""

    def test_breakdown_keys(self) -> None:
        result = compute_alignment(
            crossover=CrossoverState.BULLISH,
            adx=30.0,
            volume_multiplier=1.5,
            obv_trend=OBVTrend.RISING,
            book_imbalance=0.65,
        )
        assert result.breakdown.ema_crossover is True
        assert result.breakdown.adx_trending is True
        assert result.breakdown.volume_confirmed is True
        assert result.breakdown.obv_aligned is True
        assert result.breakdown.book_imbalance_aligned is True

    def test_all_false_breakdown(self) -> None:
        result = compute_alignment(
            crossover=CrossoverState.BEARISH,
            adx=22.0,
            volume_multiplier=0.8,
            obv_trend=OBVTrend.FALLING,
            book_imbalance=0.45,
        )
        assert result.breakdown.ema_crossover is False
        assert result.breakdown.volume_confirmed is False
        assert result.breakdown.obv_aligned is False
        assert result.breakdown.book_imbalance_aligned is False


class TestStopDistance:
    """Stop distance from ATR."""

    def test_stop_distance(self) -> None:
        assert compute_stop_distance(100.0) == pytest.approx(150.0)

    def test_stop_distance_small(self) -> None:
        assert compute_stop_distance(10.0) == pytest.approx(15.0)


class TestPositionSize:
    """Position sizing from alignment grade."""

    def test_strong(self) -> None:
        assert compute_position_size(Alignment.STRONG) == 10.0

    def test_moderate(self) -> None:
        assert compute_position_size(Alignment.MODERATE) == 8.0

    def test_weak(self) -> None:
        assert compute_position_size(Alignment.WEAK) == 5.0

    def test_no_signal(self) -> None:
        assert compute_position_size(Alignment.NO_SIGNAL) == 0.0


class TestDerivedValues:
    """Derived values computation."""

    def test_derived_strong_aligned(self) -> None:
        dv = compute_derived_values(
            atr=100.0,
            grade=Alignment.STRONG,
            regime=Regime.TRENDING_UP,
        )
        assert dv.suggested_stop_distance == pytest.approx(150.0)
        assert dv.position_size_pct == 10.0
        assert dv.regime_aligned is True

    def test_derived_ranging_not_aligned(self) -> None:
        dv = compute_derived_values(
            atr=100.0,
            grade=Alignment.STRONG,
            regime=Regime.RANGING,
        )
        assert dv.regime_aligned is False

    def test_derived_no_signal_zero_size(self) -> None:
        dv = compute_derived_values(
            atr=100.0,
            grade=Alignment.NO_SIGNAL,
            regime=Regime.TRENDING_UP,
        )
        assert dv.position_size_pct == 0.0
