"""Anthropic Claude adapter with circuit breaker."""
from __future__ import annotations

import json
import time
from typing import Any

from anthropic import AsyncAnthropic

from trustdesk.core.config import TrustDeskConfig
from trustdesk.core.constants import ERROR_IDS
from trustdesk.core.errors import LLMUnavailableError
from trustdesk.core.logging import get_logger
from trustdesk.schemas.proposal import TradeProposal
from trustdesk.schemas.signal_payload import SignalPayload

log = get_logger(__name__)

STRATEGIST_SYSTEM = (
    "You are a cryptocurrency trading strategist. Analyze the signal payload and portfolio state. "
    "If you see a trade opportunity, respond with a JSON TradeProposal. "
    'If no trade, respond with {"action": "PASS"}. Respond with ONLY valid JSON.'
)

RISK_SYSTEM = (
    "You are a risk manager. Evaluate the trade proposal against the portfolio state. "
    "Respond with a JSON object of soft check results. Keys are check names, values are status strings. "
    "Respond with ONLY valid JSON."
)

MAX_FAILURES = 3
DEFAULT_COOLDOWN = 60.0


class AnthropicClient:
    """Claude Sonnet 4 wrapper for Strategist and Risk Manager."""

    def __init__(self, config: TrustDeskConfig) -> None:
        self._config = config
        self._client = AsyncAnthropic(api_key=config.anthropic_api_key)
        self._model = config.llm_model
        self._consecutive_failures = 0
        self._available = True
        self._opened_at: float = 0.0
        self._cooldown_seconds = DEFAULT_COOLDOWN

    def is_available(self) -> bool:
        """Check if the client is available (circuit breaker state)."""
        if self._available:
            return True
        # Auto-recover after cooldown
        if time.monotonic() - self._opened_at >= self._cooldown_seconds:
            self._available = True
            self._consecutive_failures = 0
            return True
        return False

    def _record_failure(self) -> None:
        """Record a failure and potentially open the circuit."""
        self._consecutive_failures += 1
        if self._consecutive_failures >= MAX_FAILURES:
            self._available = False
            self._opened_at = time.monotonic()
            log.warning("circuit_breaker_open", failures=self._consecutive_failures)

    def _record_success(self) -> None:
        """Reset failure count on success."""
        self._consecutive_failures = 0

    async def _call(self, system: str, user_content: str) -> str:
        """Make a Claude API call with circuit breaker protection."""
        if not self.is_available():
            raise LLMUnavailableError(
                "Anthropic circuit breaker open",
                error_id=ERROR_IDS["LLM_UNAVAILABLE"],
            )

        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=2048,
                system=system,
                messages=[{"role": "user", "content": user_content}],
            )
            self._record_success()
            return response.content[0].text
        except Exception as exc:
            self._record_failure()
            raise LLMUnavailableError(
                str(exc),
                error_id=ERROR_IDS["LLM_UNAVAILABLE"],
            ) from exc

    async def strategist_evaluate(
        self, signal_payload: SignalPayload, portfolio_state: dict[str, Any],
    ) -> TradeProposal | None:
        """Send signal to Claude for trade evaluation.

        Returns:
            TradeProposal if Claude recommends a trade, None for PASS.
        """
        user_msg = json.dumps({
            "signal": signal_payload.model_dump(mode="json"),
            "portfolio": portfolio_state,
        })
        raw = await self._call(STRATEGIST_SYSTEM, user_msg)
        data = json.loads(raw)

        if data.get("action") == "PASS":
            return None
        return TradeProposal(**data)

    async def risk_evaluate_soft(
        self, proposal: TradeProposal, portfolio_state: dict[str, Any],
    ) -> dict[str, str]:
        """Send proposal to Claude for soft risk checks.

        Returns:
            Dict of check_name -> status.
        """
        user_msg = json.dumps({
            "proposal": proposal.model_dump(mode="json"),
            "portfolio": portfolio_state,
        })
        raw = await self._call(RISK_SYSTEM, user_msg)
        return json.loads(raw)
