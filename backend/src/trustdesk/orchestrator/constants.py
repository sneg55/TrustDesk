"""Orchestrator constants."""

# Queue names
PROPOSALS_QUEUE = "proposals"
VERDICTS_QUEUE = "verdicts"

# Position lifecycle
MAX_POSITION_DURATION_SECONDS = 86400  # 24 hours
POSITION_CHECK_INTERVAL_SECONDS = 30

# Node names (for graph definition)
NODE_SIGNAL = "signal_engine"
NODE_STRATEGIST = "strategist"
NODE_REPUTATION = "reputation_check"
NODE_RISK = "risk_validate"
NODE_EXECUTE = "execute"
NODE_AUDIT = "audit"
NODE_AUDIT_PASS = "audit_pass"
