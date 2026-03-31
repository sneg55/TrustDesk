"""Tests for TradeProposal schema."""
from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from trustdesk.schemas.proposal import TradeProposal


def _minimal_proposal(**overrides) -> dict:
    """Return a dict with all required fields for TradeProposal."""
    base = {
        "agent_id": "agent-alpha-01",
        "proposal_id": "prop-001",
        "timestamp": datetime(2024, 1, 15, 9, 30, 0, tzinfo=UTC),
        "action": "BUY",
        "pair": "BTC/USD",
        "size_pct": 2.5,
        "entry_price_limit": 42000.0,
        "stop_loss": 41000.0,
        "take_profit_1": 44000.0,
        "time_horizon": "4H",
        "reasoning": "EMA crossover confirmed with volume.",
        "invalidation": "Close below 41000.",
    }
    base.update(overrides)
    return base


def test_create_minimal_proposal() -> None:
    """TradeProposal is created with only required fields."""
    data = _minimal_proposal()
    proposal = TradeProposal(**data)
    assert proposal.agent_id == "agent-alpha-01"
    assert proposal.proposal_id == "prop-001"
    assert proposal.action == "BUY"
    assert proposal.pair == "BTC/USD"
    assert proposal.size_pct == 2.5
    assert proposal.entry_price_limit == 42000.0
    assert proposal.entry_type == "LIMIT"  # default
    assert proposal.stop_loss == 41000.0
    assert proposal.take_profit_1 == 44000.0
    assert proposal.time_horizon == "4H"
    assert proposal.reasoning == "EMA crossover confirmed with volume."
    assert proposal.invalidation == "Close below 41000."


def test_optional_fields_default_to_none() -> None:
    """Optional fields default to None when not provided."""
    proposal = TradeProposal(**_minimal_proposal())
    assert proposal.take_profit_2 is None
    assert proposal.alignment_score is None
    assert proposal.alignment_grade is None
    assert proposal.override_justification is None
    assert proposal.regime_at_proposal is None
    assert proposal.signals_cited is None


def test_entry_type_default_is_limit() -> None:
    """entry_type defaults to LIMIT."""
    proposal = TradeProposal(**_minimal_proposal())
    assert proposal.entry_type == "LIMIT"


def test_create_sell_proposal() -> None:
    """Action SELL is valid."""
    proposal = TradeProposal(**_minimal_proposal(action="SELL"))
    assert proposal.action == "SELL"


def test_invalid_action_raises() -> None:
    """Invalid action literal raises ValidationError."""
    with pytest.raises(ValidationError):
        TradeProposal(**_minimal_proposal(action="HOLD"))


def test_invalid_alignment_grade_raises() -> None:
    """Invalid alignment_grade literal raises ValidationError."""
    with pytest.raises(ValidationError):
        TradeProposal(**_minimal_proposal(alignment_grade="EXCELLENT"))


def test_invalid_regime_raises() -> None:
    """Invalid regime_at_proposal literal raises ValidationError."""
    with pytest.raises(ValidationError):
        TradeProposal(**_minimal_proposal(regime_at_proposal="BULLISH"))


def test_all_alignment_grades() -> None:
    """All valid alignment_grade literals are accepted."""
    for grade in ("STRONG", "MODERATE", "WEAK", "NO_SIGNAL"):
        proposal = TradeProposal(**_minimal_proposal(alignment_grade=grade))
        assert proposal.alignment_grade == grade


def test_all_regime_values() -> None:
    """All valid regime_at_proposal literals are accepted."""
    for regime in ("TRENDING_UP", "TRENDING_DOWN", "RANGING", "VOLATILE"):
        proposal = TradeProposal(**_minimal_proposal(regime_at_proposal=regime))
        assert proposal.regime_at_proposal == regime


def test_full_proposal_with_all_fields() -> None:
    """Proposal with all fields populated is valid."""
    proposal = TradeProposal(**_minimal_proposal(
        take_profit_2=46000.0,
        alignment_score=0.8,
        alignment_grade="STRONG",
        override_justification="Conviction trade based on news event.",
        regime_at_proposal="TRENDING_UP",
        signals_cited=["EMA_CROSS", "ADX_HIGH", "VOLUME_SPIKE"],
    ))
    assert proposal.take_profit_2 == 46000.0
    assert proposal.alignment_score == 0.8
    assert proposal.alignment_grade == "STRONG"
    assert proposal.override_justification == "Conviction trade based on news event."
    assert proposal.regime_at_proposal == "TRENDING_UP"
    assert proposal.signals_cited == ["EMA_CROSS", "ADX_HIGH", "VOLUME_SPIKE"]


def test_model_dump_round_trip() -> None:
    """model_dump and reconstruction produce equivalent models."""
    original = TradeProposal(**_minimal_proposal(
        take_profit_2=46000.0,
        alignment_score=0.75,
        alignment_grade="MODERATE",
        regime_at_proposal="RANGING",
        signals_cited=["EMA_CROSS"],
    ))
    dumped = original.model_dump()
    reconstructed = TradeProposal(**dumped)
    assert reconstructed == original


def test_model_dump_contains_expected_keys() -> None:
    """model_dump includes all expected keys."""
    proposal = TradeProposal(**_minimal_proposal())
    dumped = proposal.model_dump()
    expected_keys = {
        "agent_id", "proposal_id", "timestamp", "action", "pair",
        "size_pct", "entry_price_limit", "entry_type", "stop_loss",
        "take_profit_1", "take_profit_2", "time_horizon", "reasoning",
        "invalidation", "alignment_score", "alignment_grade",
        "override_justification", "regime_at_proposal", "signals_cited",
    }
    assert set(dumped.keys()) == expected_keys


def test_timestamp_is_datetime() -> None:
    """timestamp field accepts datetime objects."""
    ts = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)
    proposal = TradeProposal(**_minimal_proposal(timestamp=ts))
    assert proposal.timestamp == ts


def test_timestamp_from_string() -> None:
    """timestamp field parses ISO strings."""
    proposal = TradeProposal(**_minimal_proposal(timestamp="2024-06-01T12:00:00Z"))
    assert proposal.timestamp.year == 2024


def test_size_pct_accepts_float() -> None:
    """size_pct accepts float values."""
    proposal = TradeProposal(**_minimal_proposal(size_pct=1.5))
    assert proposal.size_pct == 1.5


def test_signals_cited_list() -> None:
    """signals_cited accepts a list of strings."""
    signals = ["EMA_20", "EMA_50", "ADX", "OBV", "BOOK_IMBALANCE"]
    proposal = TradeProposal(**_minimal_proposal(signals_cited=signals))
    assert proposal.signals_cited == signals
