"""Tests for SignalPayload, Alignment, AlignmentBreakdown, and DerivedValues schemas."""
from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from trustdesk.schemas.signal_payload import Alignment, AlignmentBreakdown, DerivedValues, SignalPayload


def _alignment_breakdown(**overrides) -> dict:
    """Return a dict with all required fields for AlignmentBreakdown."""
    base = {
        "ema_direction": True,
        "adx_strength": True,
        "volume_confirmation": True,
        "obv_trend_match": False,
        "book_imbalance_favorable": True,
    }
    base.update(overrides)
    return base


def _alignment(**overrides) -> dict:
    """Return a dict with all required fields for Alignment."""
    base = {
        "score": 0.8,
        "grade": "STRONG",
        "signals_agreeing": 4,
        "breakdown": _alignment_breakdown(),
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
        "timestamp": datetime(2024, 1, 15, 9, 30, 0, tzinfo=UTC),
        "pair": "BTC/USD",
        "price": 42000.0,
        "regime": "TRENDING_UP",
        "regime_confidence": 0.75,
        "regime_changed": False,
        "signals": {
            "ema_20": 41800.0,
            "ema_50": 41200.0,
            "adx": 32.5,
            "volume_ratio": 1.4,
        },
        "alignment": _alignment(),
        "derived": _derived_values(),
    }
    base.update(overrides)
    return base


class TestAlignmentBreakdown:
    def test_create_breakdown(self) -> None:
        """AlignmentBreakdown is created with all required fields."""
        breakdown = AlignmentBreakdown(**_alignment_breakdown())
        assert breakdown.ema_direction is True
        assert breakdown.adx_strength is True
        assert breakdown.volume_confirmation is True
        assert breakdown.obv_trend_match is False
        assert breakdown.book_imbalance_favorable is True

    def test_all_false_breakdown(self) -> None:
        """AlignmentBreakdown accepts all False values."""
        breakdown = AlignmentBreakdown(
            ema_direction=False,
            adx_strength=False,
            volume_confirmation=False,
            obv_trend_match=False,
            book_imbalance_favorable=False,
        )
        assert breakdown.ema_direction is False

    def test_model_dump_round_trip(self) -> None:
        """AlignmentBreakdown round-trips through model_dump."""
        original = AlignmentBreakdown(**_alignment_breakdown())
        reconstructed = AlignmentBreakdown(**original.model_dump())
        assert reconstructed == original

    def test_missing_field_raises(self) -> None:
        """Missing required field raises ValidationError."""
        with pytest.raises(ValidationError):
            AlignmentBreakdown(
                ema_direction=True,
                adx_strength=True,
                volume_confirmation=True,
                obv_trend_match=True,
                # missing book_imbalance_favorable
            )


class TestAlignment:
    def test_create_alignment(self) -> None:
        """Alignment is created with all required fields."""
        alignment = Alignment(**_alignment())
        assert alignment.score == 0.8
        assert alignment.grade == "STRONG"
        assert alignment.signals_agreeing == 4
        assert alignment.signals_total == 5  # default
        assert isinstance(alignment.breakdown, AlignmentBreakdown)

    def test_signals_total_default(self) -> None:
        """signals_total defaults to 5."""
        alignment = Alignment(**_alignment())
        assert alignment.signals_total == 5

    def test_signals_total_override(self) -> None:
        """signals_total can be overridden."""
        alignment = Alignment(**_alignment(signals_total=3))
        assert alignment.signals_total == 3

    def test_all_grade_values(self) -> None:
        """All valid grade literals are accepted."""
        for grade in ("STRONG", "MODERATE", "WEAK", "NO_SIGNAL"):
            alignment = Alignment(**_alignment(grade=grade))
            assert alignment.grade == grade

    def test_invalid_grade_raises(self) -> None:
        """Invalid grade literal raises ValidationError."""
        with pytest.raises(ValidationError):
            Alignment(**_alignment(grade="EXCELLENT"))

    def test_model_dump_round_trip(self) -> None:
        """Alignment round-trips through model_dump."""
        original = Alignment(**_alignment())
        dumped = original.model_dump()
        reconstructed = Alignment(**dumped)
        assert reconstructed == original

    def test_breakdown_from_dict(self) -> None:
        """breakdown can be provided as a dict and coerces to AlignmentBreakdown."""
        alignment = Alignment(**_alignment())
        assert isinstance(alignment.breakdown, AlignmentBreakdown)


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
        assert payload.pair == "BTC/USD"
        assert payload.price == 42000.0
        assert payload.regime == "TRENDING_UP"
        assert payload.regime_confidence == 0.75
        assert payload.regime_changed is False
        assert isinstance(payload.alignment, Alignment)
        assert isinstance(payload.derived, DerivedValues)

    def test_all_regime_values(self) -> None:
        """All valid regime literals are accepted."""
        for regime in ("TRENDING_UP", "TRENDING_DOWN", "RANGING", "VOLATILE"):
            payload = SignalPayload(**_signal_payload(regime=regime))
            assert payload.regime == regime

    def test_invalid_regime_raises(self) -> None:
        """Invalid regime literal raises ValidationError."""
        with pytest.raises(ValidationError):
            SignalPayload(**_signal_payload(regime="BULLISH"))

    def test_regime_changed_true(self) -> None:
        """regime_changed can be True."""
        payload = SignalPayload(**_signal_payload(regime_changed=True))
        assert payload.regime_changed is True

    def test_signals_dict_accepts_various_types(self) -> None:
        """signals dict accepts various value types."""
        signals = {
            "ema_cross": True,
            "adx": 32.5,
            "volume_ratio": 1.4,
            "note": "strong momentum",
            "levels": [41000, 42000],
        }
        payload = SignalPayload(**_signal_payload(signals=signals))
        assert payload.signals["ema_cross"] is True
        assert payload.signals["adx"] == 32.5

    def test_timestamp_from_string(self) -> None:
        """timestamp field parses ISO strings."""
        payload = SignalPayload(**_signal_payload(timestamp="2024-06-01T12:00:00Z"))
        assert payload.timestamp.year == 2024

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
            "timestamp", "pair", "price", "regime", "regime_confidence",
            "regime_changed", "signals", "alignment", "derived",
        }
        assert set(dumped.keys()) == expected_keys

    def test_alignment_nested_breakdown(self) -> None:
        """Nested breakdown data is accessible through alignment."""
        payload = SignalPayload(**_signal_payload())
        assert payload.alignment.breakdown.ema_direction is True
        assert payload.alignment.breakdown.obv_trend_match is False

    def test_realistic_no_signal_payload(self) -> None:
        """Payload with NO_SIGNAL grade and zero scores is valid."""
        no_signal_alignment = {
            "score": 0.2,
            "grade": "NO_SIGNAL",
            "signals_agreeing": 1,
            "breakdown": {
                "ema_direction": False,
                "adx_strength": False,
                "volume_confirmation": True,
                "obv_trend_match": False,
                "book_imbalance_favorable": False,
            },
        }
        derived = {"suggested_stop_distance": 0.0, "position_size_pct": 0.0, "regime_aligned": False}
        payload = SignalPayload(**_signal_payload(
            regime="RANGING",
            alignment=no_signal_alignment,
            derived=derived,
        ))
        assert payload.alignment.grade == "NO_SIGNAL"
        assert payload.derived.regime_aligned is False
