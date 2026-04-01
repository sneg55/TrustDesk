"""Tests for SignalPayload, Alignment, AlignmentBreakdown, and DerivedValues schemas."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from trustdesk.schemas.signal_payload import Alignment, AlignmentBreakdown, DerivedValues, SignalPayload


def _alignment_breakdown(**overrides) -> dict:
    """Return a dict with all required fields for AlignmentBreakdown."""
    base = {
        "ema_crossover": True,
        "adx_trending": True,
        "volume_confirmed": True,
        "obv_aligned": False,
        "book_imbalance_aligned": True,
    }
    base.update(overrides)
    return base


def _derived_values(**overrides) -> dict:
    """Return a dict with all required fields for DerivedValues."""
    base = {
        "suggested_stop_distance": 500.0,
        "position_size_pct": 2.0,
        "regime_aligned": True,
    }
    base.update(overrides)
    return base


def _signal_payload(**overrides) -> dict:
    """Return a dict with all required fields for SignalPayload."""
    base = {
        "pair": "BTCUSD",
        "price": 42000.0,
        "regime": "TRENDING_UP",
        "alignment": Alignment.STRONG,
        "alignment_score": 0.8,
        "breakdown": _alignment_breakdown(),
        "derived": _derived_values(),
        "indicators": {
            "ema_9": 41800.0,
            "ema_21": 41200.0,
            "adx_14": 32.5,
            "volume_multiplier": 1.4,
        },
    }
    base.update(overrides)
    return base


class TestAlignmentEnum:
    def test_alignment_values(self) -> None:
        """Alignment enum has correct string values."""
        assert Alignment.STRONG.value == "STRONG"
        assert Alignment.MODERATE.value == "MODERATE"
        assert Alignment.WEAK.value == "WEAK"
        assert Alignment.NO_SIGNAL.value == "NO_SIGNAL"

    def test_alignment_from_value(self) -> None:
        """Alignment enum can be constructed from string value."""
        assert Alignment("STRONG") == Alignment.STRONG
        assert Alignment("NO_SIGNAL") == Alignment.NO_SIGNAL


class TestAlignmentBreakdown:
    def test_create_breakdown(self) -> None:
        """AlignmentBreakdown is created with all required fields."""
        breakdown = AlignmentBreakdown(**_alignment_breakdown())
        assert breakdown.ema_crossover is True
        assert breakdown.adx_trending is True
        assert breakdown.volume_confirmed is True
        assert breakdown.obv_aligned is False
        assert breakdown.book_imbalance_aligned is True

    def test_all_false_breakdown(self) -> None:
        """AlignmentBreakdown accepts all False values."""
        breakdown = AlignmentBreakdown(
            ema_crossover=False,
            adx_trending=False,
            volume_confirmed=False,
            obv_aligned=False,
            book_imbalance_aligned=False,
        )
        assert breakdown.ema_crossover is False

    def test_model_dump_round_trip(self) -> None:
        """AlignmentBreakdown round-trips through model_dump."""
        original = AlignmentBreakdown(**_alignment_breakdown())
        reconstructed = AlignmentBreakdown(**original.model_dump())
        assert reconstructed == original

    def test_missing_field_raises(self) -> None:
        """Missing required field raises ValidationError."""
        with pytest.raises(ValidationError):
            AlignmentBreakdown(
                ema_crossover=True,
                adx_trending=True,
                volume_confirmed=True,
                obv_aligned=True,
                # missing book_imbalance_aligned
            )


class TestDerivedValues:
    def test_create_derived_values(self) -> None:
        """DerivedValues is created with all required fields."""
        derived = DerivedValues(**_derived_values())
        assert derived.suggested_stop_distance == 500.0
        assert derived.position_size_pct == 2.0
        assert derived.regime_aligned is True

    def test_regime_not_aligned(self) -> None:
        """regime_aligned can be False."""
        derived = DerivedValues(**_derived_values(regime_aligned=False))
        assert derived.regime_aligned is False

    def test_model_dump_round_trip(self) -> None:
        """DerivedValues round-trips through model_dump."""
        original = DerivedValues(**_derived_values())
        reconstructed = DerivedValues(**original.model_dump())
        assert reconstructed == original

    def test_missing_field_raises(self) -> None:
        """Missing required field raises ValidationError."""
        with pytest.raises(ValidationError):
            DerivedValues(suggested_stop_distance=500.0, position_size_pct=2.0)


class TestSignalPayload:
    def test_create_signal_payload(self) -> None:
        """SignalPayload is created with all required fields."""
        payload = SignalPayload(**_signal_payload())
        assert payload.pair == "BTCUSD"
        assert payload.price == 42000.0
        assert payload.regime == "TRENDING_UP"
        assert payload.alignment == Alignment.STRONG
        assert payload.alignment_score == 0.8
        assert isinstance(payload.breakdown, AlignmentBreakdown)
        assert isinstance(payload.derived, DerivedValues)

    def test_all_alignment_grades(self) -> None:
        """All alignment grades are accepted."""
        for grade in (Alignment.STRONG, Alignment.MODERATE, Alignment.WEAK, Alignment.NO_SIGNAL):
            payload = SignalPayload(**_signal_payload(alignment=grade))
            assert payload.alignment == grade

    def test_all_regime_values(self) -> None:
        """All valid regime strings are accepted."""
        for regime in ("TRENDING_UP", "TRENDING_DOWN", "RANGING", "VOLATILE"):
            payload = SignalPayload(**_signal_payload(regime=regime))
            assert payload.regime == regime

    def test_indicators_dict(self) -> None:
        """indicators dict accepts various value types."""
        indicators = {
            "ema_9": 41800.0,
            "rsi_14": 65.2,
            "book_imbalance": 0.62,
            "trade_flow": 0.5,
        }
        payload = SignalPayload(**_signal_payload(indicators=indicators))
        assert payload.indicators["ema_9"] == 41800.0

    def test_model_dump_round_trip(self) -> None:
        """SignalPayload round-trips through model_dump."""
        original = SignalPayload(**_signal_payload())
        dumped = original.model_dump()
        reconstructed = SignalPayload(**dumped)
        assert reconstructed == original

    def test_model_dump_contains_expected_keys(self) -> None:
        """model_dump includes all expected keys."""
        payload = SignalPayload(**_signal_payload())
        dumped = payload.model_dump()
        expected_keys = {
            "pair", "price", "regime", "alignment", "alignment_score",
            "breakdown", "derived", "indicators",
        }
        assert set(dumped.keys()) == expected_keys

    def test_alignment_nested_breakdown(self) -> None:
        """Nested breakdown data is accessible."""
        payload = SignalPayload(**_signal_payload())
        assert payload.breakdown.ema_crossover is True
        assert payload.breakdown.obv_aligned is False

    def test_realistic_no_signal_payload(self) -> None:
        """Payload with NO_SIGNAL grade and zero scores is valid."""
        derived = {"suggested_stop_distance": 0.0, "position_size_pct": 0.0, "regime_aligned": False}
        breakdown = {
            "ema_crossover": False,
            "adx_trending": False,
            "volume_confirmed": False,
            "obv_aligned": False,
            "book_imbalance_aligned": False,
        }
        payload = SignalPayload(**_signal_payload(
            regime="RANGING",
            alignment=Alignment.NO_SIGNAL,
            alignment_score=0.0,
            breakdown=breakdown,
            derived=derived,
        ))
        assert payload.alignment == Alignment.NO_SIGNAL
        assert payload.derived.regime_aligned is False
