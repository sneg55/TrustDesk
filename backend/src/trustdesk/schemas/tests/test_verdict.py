"""Tests for RiskVerdict and FieldModification schemas."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from trustdesk.schemas.verdict import FieldModification, RiskVerdict


def _minimal_verdict(**overrides) -> dict:
    """Return a dict with all required fields for RiskVerdict."""
    base = {
        "proposal_id": "prop-001",
        "validator_address": "0xABC123",
        "verdict": "APPROVED",
        "tier_at_verdict": "ESTABLISHED",
        "hard_checks": {"max_position": "PASS", "daily_loss": "PASS"},
        "soft_checks": {"trend_alignment": "PASS", "volatility": "WARN"},
        "reasoning": "All hard checks passed. Soft checks indicate moderate risk.",
    }
    base.update(overrides)
    return base


class TestFieldModification:
    def test_create_field_modification(self) -> None:
        """FieldModification is created with all required fields."""
        mod = FieldModification(original=2.5, approved=2.0, reason="Exceeds max position for tier.")
        assert mod.original == 2.5
        assert mod.approved == 2.0
        assert mod.reason == "Exceeds max position for tier."

    def test_model_dump_round_trip(self) -> None:
        """FieldModification round-trips through model_dump."""
        mod = FieldModification(original=5.0, approved=3.0, reason="Risk limit exceeded.")
        reconstructed = FieldModification(**mod.model_dump())
        assert reconstructed == mod

    def test_missing_required_field_raises(self) -> None:
        """FieldModification requires all three fields."""
        with pytest.raises(ValidationError):
            FieldModification(original=2.5, approved=2.0)  # missing reason


class TestRiskVerdict:
    def test_create_minimal_verdict(self) -> None:
        """RiskVerdict is created with all required fields."""
        verdict = RiskVerdict(**_minimal_verdict())
        assert verdict.proposal_id == "prop-001"
        assert verdict.validator_address == "0xABC123"
        assert verdict.verdict == "APPROVED"
        assert verdict.tier_at_verdict == "ESTABLISHED"
        assert verdict.reasoning == "All hard checks passed. Soft checks indicate moderate risk."

    def test_optional_fields_default_to_none(self) -> None:
        """Optional fields default to None."""
        verdict = RiskVerdict(**_minimal_verdict())
        assert verdict.modifications is None
        assert verdict.evidence_uri is None
        assert verdict.on_chain_tx is None

    def test_all_verdict_values(self) -> None:
        """All valid verdict literals are accepted."""
        for v in ("APPROVED", "APPROVED_WITH_MODIFICATION", "APPROVED_HARD_ONLY", "REJECTED"):
            verdict = RiskVerdict(**_minimal_verdict(verdict=v))
            assert verdict.verdict == v

    def test_invalid_verdict_raises(self) -> None:
        """Invalid verdict literal raises ValidationError."""
        with pytest.raises(ValidationError):
            RiskVerdict(**_minimal_verdict(verdict="PENDING"))

    def test_all_tier_values(self) -> None:
        """All valid tier_at_verdict literals are accepted."""
        for tier in ("UNPROVEN", "ESTABLISHED", "TRUSTED"):
            verdict = RiskVerdict(**_minimal_verdict(tier_at_verdict=tier))
            assert verdict.tier_at_verdict == tier

    def test_invalid_tier_raises(self) -> None:
        """Invalid tier_at_verdict literal raises ValidationError."""
        with pytest.raises(ValidationError):
            RiskVerdict(**_minimal_verdict(tier_at_verdict="EXPERT"))

    def test_soft_checks_as_skipped_literal(self) -> None:
        """soft_checks accepts 'SKIPPED_LLM_UNAVAILABLE' string literal."""
        verdict = RiskVerdict(**_minimal_verdict(soft_checks="SKIPPED_LLM_UNAVAILABLE"))
        assert verdict.soft_checks == "SKIPPED_LLM_UNAVAILABLE"

    def test_soft_checks_as_dict(self) -> None:
        """soft_checks accepts a dict."""
        checks = {"trend": "PASS", "momentum": "WARN"}
        verdict = RiskVerdict(**_minimal_verdict(soft_checks=checks))
        assert verdict.soft_checks == checks

    def test_modifications_with_field_modification(self) -> None:
        """modifications field accepts dict of FieldModification instances."""
        mods = {
            "size_pct": FieldModification(original=3.0, approved=2.0, reason="Exceeds tier limit."),
        }
        verdict = RiskVerdict(**_minimal_verdict(
            verdict="APPROVED_WITH_MODIFICATION",
            modifications=mods,
        ))
        assert verdict.modifications is not None
        assert "size_pct" in verdict.modifications
        assert verdict.modifications["size_pct"].original == 3.0
        assert verdict.modifications["size_pct"].approved == 2.0

    def test_modifications_with_dict_data(self) -> None:
        """modifications field accepts dict with nested dicts that coerce to FieldModification."""
        mods = {
            "size_pct": {"original": 3.0, "approved": 2.0, "reason": "Exceeds tier limit."},
        }
        verdict = RiskVerdict(**_minimal_verdict(
            verdict="APPROVED_WITH_MODIFICATION",
            modifications=mods,
        ))
        assert verdict.modifications is not None
        assert isinstance(verdict.modifications["size_pct"], FieldModification)

    def test_full_verdict_with_all_fields(self) -> None:
        """Verdict with all optional fields populated is valid."""
        mods = {
            "stop_loss": FieldModification(original=41000.0, approved=40500.0, reason="Volatility adjustment."),
        }
        verdict = RiskVerdict(**_minimal_verdict(
            verdict="APPROVED_WITH_MODIFICATION",
            modifications=mods,
            evidence_uri="ipfs://QmXXX",
            on_chain_tx="0xTXHASH",
        ))
        assert verdict.evidence_uri == "ipfs://QmXXX"
        assert verdict.on_chain_tx == "0xTXHASH"
        assert verdict.modifications is not None

    def test_model_dump_round_trip(self) -> None:
        """RiskVerdict round-trips through model_dump."""
        verdict = RiskVerdict(**_minimal_verdict(
            evidence_uri="ipfs://QmABC",
        ))
        dumped = verdict.model_dump()
        reconstructed = RiskVerdict(**dumped)
        assert reconstructed == verdict

    def test_model_dump_contains_expected_keys(self) -> None:
        """model_dump includes all expected keys."""
        verdict = RiskVerdict(**_minimal_verdict())
        dumped = verdict.model_dump()
        expected_keys = {
            "proposal_id", "validator_address", "verdict", "tier_at_verdict",
            "modifications", "hard_checks", "soft_checks", "reasoning",
            "evidence_uri", "on_chain_tx",
        }
        assert set(dumped.keys()) == expected_keys

    def test_hard_checks_dict(self) -> None:
        """hard_checks is stored as a dict of str -> str."""
        checks = {"max_position": "PASS", "daily_loss": "PASS", "leverage": "FAIL"}
        verdict = RiskVerdict(**_minimal_verdict(hard_checks=checks))
        assert verdict.hard_checks == checks
