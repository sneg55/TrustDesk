"""Auditor: deterministic trade decision recorder for ERC-8004."""

from trustdesk.auditor.auditor import Auditor
from trustdesk.auditor.reputation_lifecycle import compute_score
from trustdesk.auditor.types import FeedbackStage, ReputationEntry

__all__ = ["Auditor", "FeedbackStage", "ReputationEntry", "compute_score"]
