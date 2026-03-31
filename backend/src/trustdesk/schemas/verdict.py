"""RiskVerdict — returned by the Risk Manager after evaluating a proposal."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class FieldModification(BaseModel):
    original: float
    approved: float
    reason: str


class RiskVerdict(BaseModel):
    proposal_id: str
    validator_address: str
    verdict: Literal["APPROVED", "APPROVED_WITH_MODIFICATION", "APPROVED_HARD_ONLY", "REJECTED"]
    tier_at_verdict: Literal["UNPROVEN", "ESTABLISHED", "TRUSTED"]
    modifications: dict[str, FieldModification] | None = None
    hard_checks: dict[str, str]
    soft_checks: dict[str, str] | Literal["SKIPPED_LLM_UNAVAILABLE"]
    reasoning: str
    evidence_uri: str | None = None
    on_chain_tx: str | None = None
