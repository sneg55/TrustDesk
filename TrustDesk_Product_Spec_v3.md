# TrustDesk — Product Spec v3

**AI Trading Agents Hackathon · March 30 – April 12, 2026**

Combined submission (Kraken CLI + ERC-8004)

---

## Changelog

### v3.1 (from v3)

Narrative and architectural reframing. Four structural changes:

1. **Platform pivot.** TrustDesk is no longer positioned as "a transparent trading bot." It is now an agent-agnostic trading desk — infrastructure that any agent can plug into. The desk enforces risk controls and tracks reputation; agents bring their own strategy and signals.
2. **Reputation-gated capital.** ERC-8004 reputation now directly controls capital access. New agents start with tight limits ($100 allocation, 3% max position, 1 open trade). Proven agents unlock more. Blowups trigger automatic demotion. This makes ERC-8004 the product, not a compliance addon.
3. **Agent Interface spec added.** Defines the pluggable contract any agent must implement to connect to the desk: submit `TradeProposal` JSON, receive `RiskVerdict`, handle position lifecycle callbacks.
4. **Spec restructured into Desk Infrastructure and Demo Agent.** Signal Engine and Strategist are now scoped as the hackathon demo agent. Risk Manager, Auditor, and reputation-to-limits mapping are desk infrastructure that applies to any connected agent.

### v3 (from v2)

Addresses second-round technical review. Six targeted fixes:

1. **Dual-path validation flow.** Fast local validation for execution speed, async on-chain posting for trust record. Trade execution is no longer blocked by 15-30 second chain round-trips.
2. **LLM confidence score replaced with deterministic Signal Alignment Score.** Computed by the Signal Engine from signal agreement count. The LLM no longer self-assesses confidence.
3. **PASS decision rate-limiting.** One on-chain PASS log per hour per regime, with batched summaries. Prevents flooding the Reputation Registry during downtrends.
4. **Gas management section added.** Pre-funding strategy, faucet fallbacks, tiered write priority when gas runs low.
5. **Backtest go/no-go criteria revised.** Replaced annualized Sharpe with rolling equity curve monotonicity. Clarified partial-exit win/loss counting.
6. **LLM API circuit breaker.** Risk Manager operates in hard-limits-only mode when Anthropic API is unreachable. Strategist skips cycle gracefully.

### v2 (from v1)

1. **New Signal Engine layer** separates deterministic math from LLM reasoning. The LLM never calculates indicators, it interprets pre-computed signals.
2. **Trading strategy rebuilt from scratch.** Replaced generic MACD/RSI with an adaptive regime-detection strategy, backed by a mandatory backtesting phase before live deployment.
3. **Validation Registry redesigned as a genuinely external validator.** The Risk Manager now operates as an independent process with its own wallet, treating the Strategist as a black box it audits externally.
4. **Interim reputation signals** solve the open-trade gap. On-chain feedback is posted at trade open, on material changes, and at trade close.
5. **Kraken CLI fallback path** added. MCP is primary, subprocess with JSON parsing is secondary.
6. **Spot-only execution** clarified. No futures, no shorting. Strategy designed around long-only and cash positions.
7. **Dashboard scope tiered** into MVP, Enhanced, and Stretch layers.
8. **Social engagement plan** starts on day 1, not day 12.
9. **Leaderboard strategy** section added with capital allocation and PnL maximization tactics.
10. **Open Validation API** lets anyone post external validation responses for TrustDesk trades.

---

## One-liner

An AI trading desk that any agent can plug into — hard risk controls prevent blowups, on-chain reputation scores determine how much capital each agent earns access to, and every trade executes through Kraken CLI with a verifiable audit trail on ERC-8004.

---

## The Narrative

Anyone can build a trading agent. Nobody can prove it won't blow up.

The problem isn't intelligence — it's trust. An agent can have the best signals in the world, but the moment you give it access to real capital, you're betting it won't overtrade, stack correlated positions, or hold a loser until the account is empty. Past performance numbers are self-reported — there's no way to verify they're real. Backtests are curve-fitted to look good on history and fall apart live. The only proof that matters is a verifiable track record with real money under real constraints, where every trade is auditable and every risk check is on the record.

TrustDesk solves this. It's not a trading agent — it's a trading desk that any agent can plug into.

The desk provides market data, risk infrastructure, and execution via Kraken CLI. Agents connect to the desk and propose trades. The desk decides whether those trades happen — enforcing position limits, exposure caps, correlation checks, and drawdown rules regardless of what the agent wants. The agent is the brain. The desk is the guardrails.

New agents start small: tight limits, minimal capital access. As an agent builds a track record — verified on-chain through ERC-8004, not self-reported — its reputation score rises and it earns access to larger allocations and wider risk parameters. An agent that blows up gets throttled automatically. An agent that compounds gains and respects limits gets rewarded with more room to operate.

The desk doesn't care if the agent is an LLM, a rule-based script, or a reinforcement learning model. It only cares about results and risk behavior.

Under the hood, TrustDesk runs three layers:

- **The Strategist** is the pluggable slot. Any agent connects here — an LLM, a statistical model, a hand-coded script. The desk treats it as a black box that outputs trade proposals. For this hackathon, we demo with a Claude-powered agent, but the architecture doesn't depend on it.
- **The Risk Manager** is the desk's enforcement layer. Independent process, independent wallet. It validates every proposal against hard portfolio limits before a single dollar moves. It doesn't trust the agent. It verifies.
- **The Auditor** writes the full decision trail to ERC-8004 — proposals, risk verdicts, outcomes. This is how reputation accrues. Not a feature. The mechanism that controls capital access.

Agents bring their own signals, their own models, their own edge. The desk doesn't care how an agent makes decisions. It controls what happens after.

Here's where ERC-8004 stops being a compliance checkbox and becomes the product:

Every trade an agent makes through TrustDesk is recorded on-chain — entry, risk verdict, outcome. This builds a reputation score that isn't self-reported, isn't backtested, and can't be faked. It's computed from verified trades with real money.

Reputation directly controls what an agent can do:

| Reputation tier | Capital access | Max position | Max open trades |
|---|---|---|---|
| Unproven (new agent) | $100 | 3% of allocation | 1 |
| Established (20+ verified trades, positive PnL) | $500 | 7% | 3 |
| Trusted (50+ trades, rising equity curve, max DD < 10%) | $1,000+ | 10% | 5 |

An agent that blows through its drawdown limit gets automatically demoted — tighter limits, smaller allocation, until it proves it can behave. An agent that compounds quietly gets promoted. No human in the loop. The on-chain record is the only input.

This is trustless capital delegation. You don't have to believe an agent is good. You can check.

The demo: a live dashboard where you watch it happen in real-time. An agent proposes a trade. The Risk Manager cuts its size because correlated exposure is too high. The trade executes in under 2 seconds via Kraken CLI. The full decision lands on-chain. Click any trade in the history and trace it — proposal, risk verdict, outcome, reputation impact. Every number verifiable on the block explorer.

TrustDesk is not a trading bot. It's the desk that makes trading bots safe to deploy with real money.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     TRUSTDESK — DESK INFRASTRUCTURE                  │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    AGENT INTERFACE (API)                       │  │
│  │  Any agent connects here. Submit TradeProposal, receive       │  │
│  │  RiskVerdict, handle position lifecycle callbacks.            │  │
│  └──────────────────────────┬────────────────────────────────────┘  │
│                              │ TradeProposal (JSON)                  │
│                              ▼                                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │              ORCHESTRATOR (LangGraph)                          │  │
│  │  proposal → reputation check → risk validation → execute/skip │  │
│  └──────────┬──────────────┬──────────────────┬─────────────────┘  │
│             │              │                  │                      │
│             ▼              ▼                  ▼                      │
│  ┌─────────────────┐ ┌───────────────┐ ┌──────────────────┐       │
│  │  RISK MANAGER    │ │   AUDITOR     │ │  REPUTATION      │       │
│  │  (EXTERNAL       │ │  (determin.)  │ │  ENGINE          │       │
│  │   VALIDATOR)     │ │               │ │                  │       │
│  │                  │ │ • IPFS upload  │ │ • Reads ERC-8004 │       │
│  │ • Own wallet     │ │ • ERC-8004    │ │   reputation     │       │
│  │ • Own process    │ │   Identity &  │ │ • Maps score to  │       │
│  │ • Hard + soft    │ │   Reputation  │ │   capital tier    │       │
│  │   limit checks   │ │ • Interim +   │ │ • Sets agent's   │       │
│  │ • Reputation-    │ │   final scores│ │   risk limits     │       │
│  │   aware limits   │ │ • PASS logs   │ │ • Handles promo/  │       │
│  │ • Posts valid.   │ │               │ │   demotion        │       │
│  │   responses      │ │               │ │                  │       │
│  └─────────────────┘ └───────────────┘ └──────────────────┘       │
│                                                                     │
└──────────────┬──────────────┬───────────────────┬───────────────────┘
               │              │                   │
               ▼              ▼                   ▼
    ┌─────────────────┐ ┌────────────────────────┐
    │   KRAKEN CLI     │ │   ERC-8004             │
    │   (MCP primary,  │ │   (Base Sepolia)       │
    │    subprocess    │ │                        │
    │    fallback)     │ │ • Identity Registry    │
    │                  │ │ • Reputation Registry  │
    │ • Paper trading  │ │ • Validation Registry  │
    │ • Live execution │ │ • Open Validation API  │
    │ • Market data    │ │ • IPFS evidence store  │
    │ • Portfolio state│ │                        │
    │ • WebSocket feeds│ │                        │
    └─────────────────┘ └────────────────────────┘
               │              │
               ▼              ▼
    ┌──────────────────────────────┐    ┌──────────────────────────┐
    │   LIVE DASHBOARD (React)     │    │  PLUGGABLE AGENTS        │
    │                              │    │                          │
    │  T1: Desk activity feed     │    │  ┌────────────────────┐  │
    │  T2: PnL + portfolio        │    │  │ Demo: Claude +     │  │
    │  T3: Reputation + tiers     │    │  │ Signal Engine      │  │
    │  T4: Trade replay           │    │  │ (hackathon agent)  │  │
    │  T5: Open validator view    │    │  └────────────────────┘  │
    │                              │    │  ┌────────────────────┐  │
    └──────────────────────────────┘    │  │ Future: any LLM,   │  │
                                        │  │ script, RL model   │  │
                                        │  └────────────────────┘  │
                                        └──────────────────────────┘
```

---

## Agent Interface

Any agent connecting to TrustDesk must implement this contract. The desk is agnostic to the agent's internals — LLM, script, neural net, human-in-the-loop. It only interacts through this interface.

### Connecting to the Desk

1. **Register.** Agent registers with the desk, providing a wallet address and metadata (name, description, supported pairs). The desk registers the agent in the ERC-8004 Identity Registry and assigns it an initial reputation tier (Unproven).
2. **Receive market data (optional).** The desk exposes a market data feed via WebSocket. Agents can use it or bring their own data source.
3. **Submit proposals.** Agent submits `TradeProposal` JSON to the desk's proposal queue.
4. **Receive verdicts.** Desk returns a `RiskVerdict` (APPROVED, APPROVED_WITH_MODIFICATION, or REJECTED) with reasoning.
5. **Handle callbacks.** Desk notifies the agent on position lifecycle events: fill confirmation, partial exit, stop triggered, time-based exit, invalidation exit.

### TradeProposal Schema (required fields)

```json
{
  "agent_id": "string — registered agent identifier",
  "proposal_id": "string — unique, agent-generated",
  "timestamp": "ISO 8601",
  "action": "BUY | SELL",
  "pair": "string — e.g. BTC/USD",
  "size_pct": "number — % of agent's allocated capital",
  "entry_price_limit": "number",
  "entry_type": "LIMIT",
  "stop_loss": "number",
  "take_profit_1": "number",
  "take_profit_2": "number | null",
  "time_horizon": "string — e.g. 4h, 24h",
  "reasoning": "string — human-readable justification (logged on-chain)",
  "invalidation": "string — condition under which this trade is wrong"
}
```

Optional fields the desk will use if present: `alignment_score`, `alignment_grade`, `override_justification`, `signals_cited`. Agents that provide richer metadata get more informative on-chain records, but the desk doesn't require them.

### RiskVerdict Schema (returned by desk)

```json
{
  "proposal_id": "string",
  "verdict": "APPROVED | APPROVED_WITH_MODIFICATION | REJECTED",
  "tier_at_verdict": "UNPROVEN | ESTABLISHED | TRUSTED",
  "modifications": "object | null — field-level changes with reasons",
  "hard_checks": "object — pass/fail for each limit",
  "soft_checks": "object — pass/flag for each soft limit",
  "reasoning": "string",
  "evidence_uri": "IPFS URI"
}
```

### Position Lifecycle Callbacks

The desk notifies the agent when:
- **FILLED** — order was executed at specified price/volume
- **PARTIAL_EXIT** — TP1 hit, 50% closed
- **STOP_TRIGGERED** — stop loss hit, position closed
- **TIME_EXIT** — 24-hour time limit reached, position closed at market
- **INVALIDATION_EXIT** — regime shift or other invalidation condition met
- **DEMOTION** — agent's reputation tier dropped, limits tightened

Agents can use these callbacks to update internal state, adjust strategy, or log their own records. The desk does not require any response — callbacks are informational.

---

## Demo Agent: Signal Engine + Strategist

The following two components — Signal Engine and Strategist — are the hackathon's demo agent. They connect to TrustDesk through the Agent Interface like any other agent would. The desk infrastructure (Risk Manager, Auditor, Reputation Engine) applies identically regardless of which agent is connected.

A different team could replace this entire section with their own agent — a reinforcement learning model, a rule-based script, a different LLM — and the desk would enforce the same risk controls and reputation mechanics.

### Signal Engine

**This is not an agent. It is a deterministic Python service that feeds the demo Strategist.**

LLMs should never do math. The Signal Engine is a pure computation layer that ingests raw market data from Kraken CLI and outputs structured signal payloads. The Strategist never sees raw OHLCV data, only pre-computed, labeled signals.

### Data Ingestion

Source: Kraken CLI (`kraken ohlc`, `kraken ticker`, `kraken book`, `kraken trades`).

Connection method: MCP primary. If MCP fails, fall back to subprocess execution:
```python
# Primary: MCP
result = await mcp_client.call("kraken", "ohlc", {"pair": "BTCUSD", "interval": 15})

# Fallback: subprocess
result = subprocess.run(
    ["kraken", "ohlc", "--pair", "BTCUSD", "--interval", "15", "-o", "json"],
    capture_output=True, text=True
)
data = json.loads(result.stdout)
```

Pairs monitored: BTC/USD, ETH/USD, SOL/USD.
Timeframes: 15m (tactical), 1H (intermediate), 4H (regime).

### Indicator Calculations (pandas + ta-lib)

All computed deterministically. No LLM involvement.

**Trend indicators:**
- EMA 9, 21, 50 (on 15m and 1H)
- EMA crossover state (bullish/bearish/neutral)
- ADX (trend strength, 14-period)

**Momentum indicators:**
- RSI (14-period, on 1H)
- Stochastic RSI (for oversold/overbought confluence)
- Rate of Change (12-period)

**Volatility indicators:**
- ATR (14-period, used for stop placement and position sizing)
- Bollinger Band width (squeeze detection)
- Keltner Channel (confirms Bollinger squeeze)

**Volume indicators:**
- Volume relative to 20-period SMA (volume multiplier)
- On-Balance Volume (OBV) trend direction
- Volume-Weighted Average Price (VWAP, intraday anchor)

**Market structure:**
- Order book imbalance ratio (bid depth vs ask depth from `kraken book`)
- Recent trade flow direction (buy vs sell volume from `kraken trades`)
- Spread percentage

### Regime Detection

The Signal Engine classifies the current market into one of four regimes. This is the most important output because it determines *which* strategy variant the Strategist should deploy.

**Regimes:**

| Regime | Detection criteria | Strategy implication |
|---|---|---|
| **TRENDING_UP** | ADX > 25, EMA 9 > 21 > 50, OBV rising | Trend-following. Buy dips to EMA 21. Trail stops with ATR. |
| **TRENDING_DOWN** | ADX > 25, EMA 9 < 21 < 50, OBV falling | Stay in cash. Long-only constraint means no position is the right position. |
| **RANGING** | ADX < 20, Bollinger width contracting, price between EMA 21 and 50 | Mean reversion. Buy at Bollinger lower band, sell at upper. Tight stops. |
| **VOLATILE** | ATR > 2x 20-period average, Bollinger width expanding rapidly | Reduce position sizes by 50%. Widen stops. Only take STRONG alignment (5/5). |

Regime is re-evaluated every 15 minutes. Transitions are logged and included in the signal payload.

### Signal Payload Output

The Signal Engine outputs a structured JSON payload every cycle. This is what the Strategist receives, not raw candle data.

```json
{
  "timestamp": "2026-04-01T14:30:00Z",
  "pair": "BTC/USD",
  "price": 68150.20,
  "regime": "TRENDING_UP",
  "regime_confidence": 0.82,
  "regime_changed": false,
  "signals": {
    "ema_crossover": "BULLISH",
    "ema_crossover_bars_ago": 3,
    "adx": 31.4,
    "rsi_1h": 52.3,
    "stoch_rsi": 0.38,
    "atr_14": 420.50,
    "bollinger_squeeze": false,
    "volume_multiplier": 1.85,
    "obv_trend": "RISING",
    "vwap_position": "ABOVE",
    "book_imbalance": 0.62,
    "trade_flow": "BUY_DOMINANT"
  },
  "alignment": {
    "score": 0.80,
    "grade": "MODERATE",
    "signals_agreeing": 4,
    "signals_total": 5,
    "breakdown": {
      "ema_direction": true,
      "adx_strength": true,
      "volume_confirmation": true,
      "obv_trend_match": true,
      "book_imbalance_favorable": false
    }
  },
  "derived": {
    "suggested_stop_distance": 630.75,
    "position_size_pct": 8.0,
    "regime_aligned": true
  }
}
```

### Signal Alignment Score (replacing LLM confidence)

The judge's feedback identified a fundamental contradiction: the Signal Engine exists because LLMs shouldn't do math, yet v2 let the LLM self-assess its own confidence score. v3 fixes this with a deterministic Signal Alignment Score computed entirely by the Signal Engine.

**Computation:** Count how many of the five key directional signals agree with the proposed trade direction.

| Signal | Long-aligned condition | Weight |
|---|---|---|
| EMA crossover direction | BULLISH | 1 |
| ADX trend strength | > 25 (trending) or < 20 (ranging, for mean-reversion setups) | 1 |
| Volume confirmation | volume_multiplier > 1.2x | 1 |
| OBV trend match | RISING (for longs) | 1 |
| Order book imbalance | book_imbalance > 0.55 (bid-heavy for longs) | 1 |

**Score = signals_agreeing / signals_total**

| Score | Grade | Trading implication |
|---|---|---|
| 5/5 = 1.00 | STRONG | Full position size. All signals aligned. |
| 4/5 = 0.80 | MODERATE | Default position size. Acceptable alignment. |
| 3/5 = 0.60 | WEAK | Reduced position (50%). Marginal setup. |
| ≤2/5 = 0.40 or below | NO_SIGNAL | Below threshold. Strategist should output PASS. |

The Risk Manager uses this score directly for its threshold checks instead of relying on an LLM-generated number. The `alignment.breakdown` field tells both the Strategist and Risk Manager exactly which signals agree and which don't, so disagreements are traceable to specific data points rather than opaque model outputs.

**The Strategist can still override.** If alignment is WEAK (0.60) but the Strategist sees a structural reason to trade (e.g., "book imbalance is 0.53, just below threshold, and a large bid just appeared in the last 30 seconds"), it can propose the trade with an explicit override note. The Risk Manager then evaluates whether the override reasoning is sound. This preserves LLM judgment where it adds value while grounding the baseline in math.

The `derived` section is computed by the Signal Engine using fixed rules (e.g., stop distance = 1.5x ATR, position size = Kelly criterion capped at 10%). The Strategist can override these with reasoning, but the defaults are mathematically sound.

---

### The Strategist (Demo Agent's LLM)

**Role:** Interpret Signal Engine output and produce trade proposals via the Agent Interface.

This is the demo agent's decision-maker. It receives pre-computed signals from the Signal Engine and decides whether they warrant action. Its value-add is contextual interpretation: "The EMA crossover is bullish, but the regime just changed from RANGING to TRENDING_UP only 3 bars ago, so this might be a false breakout. Wait for ADX to confirm above 25." This is where the LLM shines — in judgment, not arithmetic.

A different agent connecting to TrustDesk would replace this component entirely and submit its own `TradeProposal` objects through the Agent Interface. The desk doesn't care how the proposal was generated.

### System Prompt (condensed)

```
You are TrustDesk's Strategist, a senior quantitative analyst.

You receive structured signal payloads from the Signal Engine.
You NEVER calculate indicators yourself. All math is pre-computed and authoritative.
The Signal Alignment Score is computed deterministically. Do NOT invent your own confidence number.

Your job:
1. Interpret the signals in context of the current regime.
2. Decide: PROPOSE a trade, or PASS (no action).
3. If proposing, provide explicit reasoning a risk manager can audit.

Decision thresholds based on Signal Alignment Score:
- STRONG (1.00): Always eligible to propose.
- MODERATE (0.80): Eligible to propose. Default path.
- WEAK (0.60): Only propose if you can cite a specific structural override reason. You MUST include an override_justification field explaining why you're trading despite weak alignment.
- NO_SIGNAL (≤0.40): Output PASS. No overrides.

Regime-specific behavior:
- TRENDING_UP: Look for pullback entries. Favor BTC over alts unless alt signals are stronger. Trail positions.
- TRENDING_DOWN: Default to PASS. Long-only means sitting in cash IS the trade.
- RANGING: Look for mean-reversion setups at Bollinger extremes. Small positions.
- VOLATILE: Only take signals with alignment STRONG. Reduce default position size by 50%.

You MUST include:
- Which signals drove the decision (cite them explicitly from the alignment breakdown)
- The Signal Alignment Score and grade (copied from payload, not invented)
- A clear invalidation condition ("this trade is wrong if X happens")

Output format: JSON TradeProposal.
```

### Trade Proposal Object (revised)

```json
{
  "proposal_id": "prop_20260401_001",
  "timestamp": "2026-04-01T14:32:00Z",
  "action": "BUY",
  "pair": "BTC/USD",
  "size_pct": 8.0,
  "entry_price_limit": 68200.00,
  "entry_type": "LIMIT",
  "stop_loss": 67519.25,
  "take_profit_1": 69010.00,
  "take_profit_2": 69870.00,
  "time_horizon": "4h",
  "alignment_score": 0.80,
  "alignment_grade": "MODERATE",
  "override_justification": null,
  "regime_at_proposal": "TRENDING_UP",
  "signals_cited": [
    "ema_crossover: BULLISH (3 bars ago, confirmed) ✓",
    "adx: 31.4 (strong trend) ✓",
    "volume_multiplier: 1.85 (above 1.2x threshold) ✓",
    "obv_trend: RISING (matches long direction) ✓",
    "book_imbalance: 0.52 (below 0.55 threshold) ✗"
  ],
  "reasoning": "Trend regime confirmed with ADX above 25. EMA crossover 3 bars old with rising volume and OBV. Book imbalance is slightly below threshold at 0.52, but 4/5 signals agree. Entering on a limit at current ask. Stop at 1.5x ATR below entry. Two profit targets: TP1 at 1:1 R:R (take 50%), TP2 at 2.5:1 R:R (trail remainder).",
  "invalidation": "Close immediately if regime shifts to TRENDING_DOWN or VOLATILE before TP1 is hit."
}
```

**Key changes from v2:** The `confidence` field is gone. Replaced by `alignment_score` and `alignment_grade`, both copied directly from the Signal Engine payload (the LLM does not generate these numbers). The `override_justification` field is null when alignment is MODERATE or STRONG, and required when the Strategist proposes a trade despite WEAK alignment. The `signals_cited` field now includes ✓/✗ markers matching the alignment breakdown, making it trivially auditable.

### Cycle Frequency

- **Active regime (TRENDING_UP, RANGING):** Evaluate every 5 minutes.
- **Passive regime (TRENDING_DOWN):** Evaluate every 15 minutes (conserve API calls, nothing to do).
- **Volatile regime:** Evaluate every 2 minutes (faster reaction needed).

### No-Trade is a Valid Output

In TRENDING_DOWN regime, the Strategist will mostly output PASS decisions. This is correct behavior for a long-only strategy. The Auditor still logs PASS decisions to the on-chain record to demonstrate the agent's discipline. Passes with reasoning ("chose not to trade because...") are more impressive to judges than blind activity.

---

---

## Desk Infrastructure

The following components are TrustDesk's core — they apply to every connected agent, regardless of how that agent generates trade proposals.

### The Risk Manager (External Validator)

**This is desk infrastructure, not part of any agent.**

The Risk Manager operates as an independent process with its own wallet. It treats every connected agent as a black box to be audited, not trusted. It doesn't care how a proposal was generated — it only evaluates whether the proposal is safe to execute given the agent's current reputation tier, portfolio state, and risk limits.

### Separation Architecture

| Property | Strategist | Risk Manager |
|---|---|---|
| Process | Main TrustDesk process | Separate process (can run on different machine) |
| Wallet | TrustDesk agent wallet (0xABC...) | Independent validator wallet (0xDEF...) |
| Data access | Signal Engine + Kraken CLI | Reads proposals from on-chain/IPFS + Kraken CLI independently |
| ERC-8004 role | Registered agent (Identity Registry) | Registered validator (posts `validationResponse()`) |
| Trust relationship | The entity being validated | The independent party validating |

### Reputation-to-Limits Mapping

This is TrustDesk's core mechanism: on-chain reputation directly controls what an agent is allowed to do. The Risk Manager reads the agent's ERC-8004 reputation score before evaluating any proposal and sets hard limits accordingly.

**Tier definitions:**

| Tier | Entry criteria | Capital allocation | Max position | Max open trades | Max daily loss |
|---|---|---|---|---|---|
| **Unproven** | New agent, < 20 verified trades | $100 | 3% of allocation | 1 | 3% of allocation |
| **Established** | 20+ verified trades, cumulative PnL > 0, max DD < 15% | $500 | 7% of allocation | 3 | 5% of allocation |
| **Trusted** | 50+ trades, rolling 10-day equity rising 60%+ of the time, max DD < 10% | $1,000+ | 10% of allocation | 5 | 5% of allocation |

**How the desk reads reputation:**

1. On each proposal, the Orchestrator queries the ERC-8004 Reputation Registry for the agent's feedback history.
2. The Reputation Engine computes: total verified trades (count of `trade_close` feedback entries), cumulative PnL (sum of score deltas from neutral 50), max drawdown (from sequential score entries), and rolling equity trend.
3. The Reputation Engine returns the agent's current tier + the corresponding limits to the Risk Manager.
4. The Risk Manager applies these as the agent's hard limits for this proposal.

**Promotion:** Checked after every `trade_close` feedback entry. If the agent newly meets the next tier's criteria, it is promoted immediately. The Auditor logs the promotion on-chain as a `tier_change` feedback entry with `score = 60` (positive event).

**Demotion:** Triggered by any of:
- Max drawdown exceeded for current tier (> 15% for Established, > 10% for Trusted)
- 5 consecutive losses at any tier
- Daily loss limit breached

Demotion drops the agent one tier and logs on-chain as a `tier_change` feedback entry with `score = 40` (negative event). The agent's position limits and capital allocation tighten immediately. Existing positions are not force-closed, but no new positions can be opened until the current exposure fits within the new tier's limits.

**Cooldown after demotion:** Agent must complete 5 verified trades at the lower tier before being eligible for re-promotion. This prevents oscillation.

### How It Works: Dual-Path Validation

The v2 spec routed every validation through on-chain round-trips, introducing 15-30 seconds of latency per trade. In volatile crypto markets, this delay can make a limit order stale before it's even placed. v3 fixes this with a dual-path design modeled after how institutional trading actually works: execute first, compliance logs it after.

**Fast Path (execution gate, sub-second):**

1. Strategist publishes a proposal to the local message queue.
2. Risk Manager receives the proposal instantly via the internal queue.
3. Risk Manager independently queries Kraken CLI for portfolio state.
4. Risk Manager evaluates hard limits + soft limits (LLM).
5. Risk Manager returns verdict to Orchestrator via local queue.
6. If APPROVED or APPROVED_WITH_MODIFICATION, the trade executes immediately.

Total latency: 1-3 seconds (dominated by LLM evaluation of soft limits).

**Trust Path (on-chain record, async, non-blocking):**

After the fast path completes (whether the trade executed or was vetoed), both the proposal and verdict are posted to ERC-8004 asynchronously:

1. Orchestrator uploads proposal to IPFS. (background task)
2. Orchestrator calls `validationRequest()` on the Validation Registry from the TrustDesk wallet. (background task)
3. Risk Manager uploads verdict to IPFS. (background task)
4. Risk Manager calls `validationResponse()` on the Validation Registry from its own wallet. (background task)

Total time to chain confirmation: 15-60 seconds. But the trade is already live.

**Consistency guarantee:** The fast path verdict and trust path verdict are always identical, because they originate from the same evaluation. The trust path is a retroactive attestation of a decision that already happened, not a separate evaluation. If the on-chain write fails, it enters the retry queue (see Gas Management). The dashboard shows both states: "Executed ✓ | On-chain: pending..." → "Executed ✓ | On-chain: confirmed ✓".

**Why this is honest, not a compromise:** This mirrors how real financial compliance works. A trader doesn't wait for the compliance department to countersign before hitting "buy." They execute within pre-approved limits, and compliance reviews the audit trail after. The ERC-8004 record is the audit trail, not the execution gate. Judges familiar with TradFi will recognize this pattern. Judges from the ERC-8004 team will appreciate that the on-chain data is still complete and verifiable, it's just not synchronous.

```
FAST PATH (sub-second, local)         TRUST PATH (async, on-chain)

Strategist → Queue → Risk Manager     ┌─ IPFS upload (proposal)
                  ↓                    ├─ validationRequest() [TrustDesk wallet]
            Verdict (local)            ├─ IPFS upload (verdict)
                  ↓                    └─ validationResponse() [Risk Manager wallet]
         Execute / Skip                         ↓
                  ↓                    On-chain record confirmed
         Dashboard: "Executed ✓"       Dashboard: "On-chain ✓"
```

### Risk Evaluation Checklist

The Risk Manager runs these checks in order. Any FAIL stops the trade.

**Hard limits (deterministic, non-negotiable, reputation-tier-dependent):**
- Position size ≤ tier max (Unproven: 3%, Established: 7%, Trusted: 10%)
- Total open exposure ≤ 40% of agent's allocated capital
- Daily realized loss ≤ tier max (Unproven: 3%, Established/Trusted: 5%)
- Max open positions: tier max (Unproven: 1, Established: 3, Trusted: 5)
- Min time between trades on same pair: 30 minutes

**Soft limits (LLM evaluates with reasoning):**
- Correlation check: Would this trade push correlated exposure above 60%?
- Regime alignment: Does the proposal match the current regime? (Cross-check Signal Engine independently.)
- Drawdown headroom: Is there enough room before the -15% max drawdown to absorb this trade's worst-case loss?
- Invalidation plausibility: Is the Strategist's stated invalidation condition actually monitorable?
- Alignment score calibration: Does the Signal Alignment Score match the proposal's aggressiveness? (e.g., a WEAK 0.60 alignment proposing a 10% position is suspicious.)
- Override scrutiny: If `override_justification` is present, is the reasoning sound? Override proposals receive extra skepticism.

### LLM API Circuit Breaker

If the Anthropic API is unreachable or rate-limited, the Risk Manager and Strategist degrade gracefully:

**Strategist (LLM unavailable):**
- Skip the current evaluation cycle. No proposal generated.
- Log: `"strategist_status": "SKIPPED_LLM_UNAVAILABLE"`.
- Retry next cycle. Existing positions continue to be managed by exchange-side stops and the Orchestrator's time-based exit rules.

**Risk Manager (LLM unavailable):**
- Switch to **hard-limits-only mode.** All five hard limit checks still run (they're deterministic, no LLM needed).
- Soft limit checks are skipped entirely.
- If all hard limits pass, the trade can execute with a flag in the verdict:

```json
{
  "verdict": "APPROVED_HARD_ONLY",
  "soft_checks": "SKIPPED_LLM_UNAVAILABLE",
  "reasoning": "LLM unavailable. Hard limits all pass. Soft limit evaluation deferred."
}
```

- This is logged on-chain with a distinct tag (`"hard_only_validation"`) so judges can see exactly when and why soft checks were skipped.
- If any hard limit fails, the trade is rejected normally. Hard limits are the safety floor, they never need LLM reasoning.

**Recovery:** When the LLM becomes available again, both agents resume normal operation on the next cycle. No manual intervention required. The dashboard shows a yellow indicator during hard-limits-only mode.

### Risk Verdict Object (revised)

```json
{
  "proposal_id": "prop_20260401_001",
  "validator_address": "0xDEF...",
  "verdict": "APPROVED_WITH_MODIFICATION",
  "modifications": {
    "size_pct": {"original": 8.0, "approved": 5.5, "reason": "ETH position creates 0.87 BTC correlation. Reducing to keep correlated exposure at 58%."},
    "stop_loss": {"original": 67519.25, "approved": 67519.25, "reason": "Acceptable. Within 1.5x ATR."}
  },
  "hard_checks": {
    "position_size": "PASS (5.5% < 10%)",
    "total_exposure": "PASS (23% + 5.5% = 28.5% < 40%)",
    "daily_loss": "PASS (current: -1.2%, limit: -5%)",
    "max_positions": "PASS (2/5)",
    "cooldown": "PASS (last BTC trade: 2h ago)"
  },
  "soft_checks": {
    "correlation": "FLAGGED, adjusted size from 8% to 5.5%",
    "regime_alignment": "PASS, independently confirmed TRENDING_UP",
    "drawdown_headroom": "PASS, 13.8% headroom remaining",
    "invalidation_plausible": "PASS, regime shift is monitorable",
    "alignment_calibration": "PASS, 0.80 MODERATE alignment with 5.5% position is proportionate",
    "override_scrutiny": "N/A, no override requested"
  },
  "evidence_uri": "ipfs://bafybeig.../risk_verdict_001.json",
  "on_chain_tx": "0x..."
}
```

### Adaptive Risk Parameters

The Risk Manager adjusts its own parameters based on recent performance. This creates a feedback loop that judges can inspect on-chain.

| Condition | Adjustment |
|---|---|
| 3 consecutive losses | Reduce max position size from 10% to 7%. Raise min alignment threshold from MODERATE (0.60) to STRONG (1.00). Log parameter change on-chain. |
| Daily drawdown > 3% | Raise min alignment threshold to STRONG (1.00). Reject all override proposals. Log on-chain. |
| 5 consecutive wins | No change. The Risk Manager is designed to be skeptical, not euphoric. |
| Regime shift to VOLATILE | Automatically halve all soft limits. Log on-chain. |

Every parameter adjustment is recorded as a validation artifact with a reasoning URI, creating a visible record of the Risk Manager adapting to market conditions.

---

### The Auditor

**Desk infrastructure. Deterministic process. Not an LLM.**

The Auditor records every decision made through TrustDesk to ERC-8004 — regardless of which agent submitted the proposal. It handles interim reputation signals, final trade outcomes, and the open validation API.

### Reputation Lifecycle (solving the open-trade gap)

The judge correctly identified that waiting until trade close to post reputation feedback creates a data gap. The revised approach posts feedback at three stages:

**Stage 1: Trade Opened**
```json
{
  "type": "TRADE_OPENED",
  "score": 50,
  "tag": "trade_open",
  "skill": "BTC/USD",
  "evidence_uri": "ipfs://bafybeig.../decision_001_open.json",
  "context": {
    "entry_price": 68200.00,
    "size_pct": 5.5,
    "regime": "TRENDING_UP",
    "risk_verdict": "APPROVED_WITH_MODIFICATION"
  }
}
```
Score starts at 50 (neutral). The feedback record shows the trade exists and was validated.

**Stage 2: Material Change (optional, event-driven)**

Posted when: unrealized PnL crosses ±2%, regime shifts, or Risk Manager triggers a parameter adjustment.
```json
{
  "type": "TRADE_UPDATE",
  "score": 62,
  "tag": "trade_update",
  "skill": "BTC/USD",
  "evidence_uri": "ipfs://bafybeig.../decision_001_update.json",
  "context": {
    "unrealized_pnl_pct": 1.2,
    "time_in_trade": "2h15m",
    "stop_moved_to_breakeven": true
  }
}
```

**Stage 3: Trade Closed**
```json
{
  "type": "TRADE_CLOSED",
  "score": 78,
  "tag": "trade_close",
  "skill": "BTC/USD",
  "evidence_uri": "ipfs://bafybeig.../decision_001_close.json",
  "context": {
    "entry_price": 68200.00,
    "exit_price": 69010.00,
    "realized_pnl_pct": 1.19,
    "realized_pnl_usd": 4.62,
    "hold_duration": "3h42m",
    "exit_reason": "TP1_HIT"
  }
}
```

Score mapping: realized PnL percentage → 0-100 scale. Losses map to 0-49, breakeven = 50, profits map to 51-100. The formula: `score = min(100, max(0, 50 + (pnl_pct * 20)))`. Capped so a single outlier trade doesn't dominate.

### PASS Decision Logging (Rate-Limited)

When the Strategist outputs PASS (no trade), the Auditor logs it, but with rate-limiting to avoid flooding the Reputation Registry during extended downtrends.

**Rate limit:** One on-chain PASS entry per hour per regime. Individual 5-minute or 15-minute evaluation cycles are batched into hourly summaries.

```json
{
  "type": "PASS_SUMMARY",
  "score": 55,
  "tag": "no_trade",
  "skill": "MARKET_OVERVIEW",
  "evidence_uri": "ipfs://bafybeig.../pass_batch_001.json",
  "context": {
    "regime": "TRENDING_DOWN",
    "window": "2026-04-05T12:00:00Z to 2026-04-05T13:00:00Z",
    "cycles_evaluated": 4,
    "all_pass": true,
    "summary_reason": "Long-only constraint. No actionable setup in downtrend across 4 evaluation cycles.",
    "pairs_evaluated": ["BTC/USD", "ETH/USD", "SOL/USD"]
  }
}
```

The IPFS evidence file contains the full detail of each individual cycle's PASS reasoning. The on-chain entry is the summary. This preserves the discipline narrative (judges see consistent PASS entries with reasoning) without generating 96 transactions per day in a sustained downtrend.

**Exception:** If a regime *change* triggers a PASS (e.g., TRENDING_UP → TRENDING_DOWN), that gets its own immediate on-chain entry regardless of the hourly rate limit, because regime transitions are material events.

PASS scores slightly above 50 because disciplined non-trading in adverse conditions is positive behavior. This creates on-chain evidence that the agent knows when NOT to trade, which is arguably more impressive than blind activity.

### Open Validation API

To make the Validation Registry usage genuinely open, TrustDesk publishes a simple smart contract endpoint that allows *anyone* to post a validation response for any TrustDesk trade.

**Contract: TrustDeskOpenValidator.sol**
```solidity
// Simplified interface
function validateTrade(
    uint256 agentId,
    bytes32 requestHash,    // Hash of the original trade proposal
    bool approved,          // External validator's opinion
    string calldata reason, // Why they agree/disagree
    string calldata evidenceURI
) external {
    // Calls ValidationRegistry.validationResponse(...)
    // Emits event for dashboard to display
}
```

Anyone with a Base Sepolia wallet can call this. The dashboard displays external validations alongside the Risk Manager's internal validation, creating a visible comparison. Even if no external validators participate during the hackathon, the infrastructure being publicly callable is a strong signal to judges.

---

## Demo Agent: Trading Strategy

*This section describes the strategy used by the hackathon demo agent (Claude + Signal Engine). It is not part of the desk infrastructure. A different agent connecting to TrustDesk would implement its own strategy and submit proposals through the Agent Interface.*

### Design Principles

1. **Long-only, spot-only.** Kraken spot trading does not support native shorting. No futures complexity. Cash is a valid position.
2. **Regime-adaptive.** The strategy does different things in different market conditions rather than applying one approach universally.
3. **Backtested before deployment.** No strategy goes live without at least 30 days of historical validation.
4. **Fewer trades, higher conviction.** In a 14-day window, 15-25 high-quality trades beat 200 noisy ones. Each trade should have a clear thesis.
5. **Asymmetric risk/reward.** Every trade targets minimum 2:1 reward/risk. Partial exits lock in profits while letting winners run.

### Market Selection

| Asset | Why | Regime sensitivity |
|---|---|---|
| BTC/USD | Highest liquidity, tightest spreads, most reliable technical patterns | Primary in all regimes |
| ETH/USD | Second most liquid, tends to amplify BTC moves | Secondary, only in TRENDING_UP |
| SOL/USD | Higher volatility, bigger moves, more risk | Only in TRENDING_UP with STRONG signals |

In TRENDING_DOWN or VOLATILE regimes, the strategy contracts to BTC-only or full cash.

### Strategy Variants by Regime

**TRENDING_UP: Pullback Continuation**
- Wait for price to pull back to EMA 21 on 1H timeframe.
- Confirm with volume contraction during pullback (volume multiplier < 0.8x), then expansion on the bounce (> 1.2x).
- Enter with limit order at EMA 21 level.
- Stop: Below the pullback low or 1.5x ATR, whichever is tighter.
- TP1: Prior swing high (take 50%). TP2: 2.5x risk distance (trail remainder with 1x ATR trailing stop).

**RANGING: Bollinger Mean Reversion**
- Enter long when price touches lower Bollinger Band AND Stochastic RSI < 0.2 AND book imbalance > 0.55 (bid-heavy).
- Small position (5% max, vs 10% max in trending).
- Stop: Below lower Bollinger Band by 0.5x ATR.
- TP: Middle Bollinger Band (take 100%, no trailing, quick in-and-out).

**TRENDING_DOWN: Cash**
- No new positions. Manage existing positions only (tighten stops, take profits if available).
- Log PASS decisions with reasoning to build on-chain evidence of discipline.

**VOLATILE: Reduced Exposure**
- Same entries as the current base regime (trending or ranging) but with 50% position size and 2x ATR stops.
- Only take signals with alignment grade STRONG (5/5).
- Max 1 open position.

### Backtesting Phase

Before any live or paper trading, the Signal Engine + Strategy logic runs against 90 days of historical Kraken OHLCV data.

**Backtest output:**
- Total trades, win rate, average win/loss ratio
- Max drawdown, Sharpe ratio, Sortino ratio
- Regime distribution (what % of time in each regime)
- Performance breakdown by regime
- Equity curve visualization

**Go/no-go criteria:**
- Rolling equity curve test: the 10-day rolling equity must be rising for at least 60% of the backtest period. This is harder to overfit than point-in-time Sharpe and directly relevant to a 14-day competition window.
- Max drawdown < 15%.
- At least 20 completed trades in the backtest period.
- Average win > 1.5x average loss (ensures asymmetric R:R is working).
- No single regime contributes more than 80% of total PnL (proves the strategy isn't only viable in one market condition).

**Partial-exit counting rules:**

Trades with split exits (TP1 at 50%, trailing TP2 at 50%) are counted as a single trade with a blended result:

| Scenario | How it's counted |
|---|---|
| TP1 fills at +1R, TP2 fills at +2.5R | WIN. Blended PnL = average of both legs. |
| TP1 fills at +1R, TP2 stopped at breakeven | WIN. Blended PnL = (1R * 0.5 + 0R * 0.5) = +0.5R. |
| TP1 fills at +1R, TP2 stopped at -0.3R | WIN. Blended PnL = (1R * 0.5 + (-0.3R) * 0.5) = +0.35R. |
| Stop hit before TP1 | LOSS. Full position stopped at -1R. |
| Time-based exit (24h) before any target | Counted at realized PnL, win or loss. |

A trade is a WIN if blended PnL > 0, LOSS if < 0, BREAKEVEN if within ±0.05R (rounded to zero for counting purposes).

If the backtest fails, adjust parameters (ATR multiplier, EMA periods, regime thresholds) and re-run. Do not deploy a strategy that hasn't passed backtesting.

### Position Management Rules

| Rule | Implementation |
|---|---|
| Entry | Limit orders only. No market orders. Reduces slippage. |
| Stop loss | Set immediately after fill via `kraken order`. Stored on exchange, not local. Exchange-side stops survive process crashes. |
| TP1 (50% exit) | Limit sell at 1:1 R:R or prior structure, whichever is closer. |
| TP2 (remaining 50%) | Trailing stop at 1x ATR. Updated every 15 minutes. |
| Breakeven move | After TP1 is filled, move stop to entry price + spread. |
| Time-based exit | If a trade hasn't hit TP1 or stop within 24 hours, close at market. Avoid holding stale positions. |
| Invalidation exit | If regime shifts to TRENDING_DOWN while in a TRENDING_UP trade, close immediately regardless of PnL. |

---

## Leaderboard Strategy

The Kraken Challenge ranks agents by net PnL (realized + unrealized). This section addresses how to maximize ranking.

### Capital Allocation

The hackathon doesn't specify a fixed starting capital. Decisions:
- Fund the Kraken account with enough to make absolute PnL meaningful. $500-1000 is a reasonable starting point.
- Focus on percentage returns. If the leaderboard rewards absolute PnL, larger capital helps. If relative, capital doesn't matter.
- Keep 60% in cash at all times as a baseline. This is the "defense" that prevents large drawdowns from taking you out of contention.

### PnL Maximization Tactics

- **Compound winners.** After a winning trade, the next position size can be slightly larger (up to the 10% cap) since the portfolio has grown.
- **Cut losers fast.** The 1.5x ATR stop and 24-hour time exit prevent small losses from becoming large ones.
- **Trade more in favorable regimes.** In TRENDING_UP with high ADX, increase cycle frequency to 2 minutes and take more setups. In TRENDING_DOWN, don't force trades just to generate activity.
- **End-of-competition awareness.** In the final 48 hours, tighten stops on all open positions. A late drawdown is worse than modest gains, because it erases days of accumulated PnL.

### What If PnL is Flat or Negative?

Flat PnL means the risk system is working — capital is preserved while other bots blow up. In a 14-day window, the agent that finishes at 0% while competitors finish at -15% is the better agent. More importantly, TrustDesk's value isn't a single agent's PnL — it's the desk infrastructure. A flat result with a working reputation-gated platform beats a positive result from a black-box bot with no trust story.

Defense mode is more nuanced than v1's binary "shut down at -10%":

| Drawdown level | Response |
|---|---|
| 0% to -3% | Normal operation. |
| -3% to -5% | Raise min alignment to STRONG (1.00). Reduce max position to 7%. Log on-chain. |
| -5% to -8% | BTC-only. Max 1 open position. STRONG alignment required. Reject all overrides. Log on-chain. |
| -8% to -12% | No new trades. Manage existing only. Post PASS summaries with reasoning. |
| Below -12% | Full cash. Sit out until a clear regime change offers a high-conviction re-entry. |

Each transition is logged on-chain via the Auditor, showing adaptive risk management rather than a binary kill switch.

---

## ERC-8004 Integration (Revised)

### Identity Registry

**One-time setup.** Register TrustDesk as an agent.

```json
{
  "type": "agent-registration-v1",
  "metadata": {
    "name": "TrustDesk",
    "description": "Agent-agnostic trading desk with reputation-gated capital access and on-chain audit trail.",
    "version": "2.0.0",
    "capabilities": ["spot-trading", "risk-management", "regime-detection"],
    "pairs": ["BTC/USD", "ETH/USD", "SOL/USD"]
  },
  "endpoints": {
    "mcp": null,
    "dashboard": "https://trustdesk.vercel.app",
    "open_validator": "0x...(TrustDeskOpenValidator contract address)"
  },
  "trust": {
    "supportedTrust": ["reputation", "validation"],
    "validatorAddress": "0xDEF...(Risk Manager wallet)"
  },
  "wallet": {
    "address": "0xABC...(TrustDesk agent wallet)",
    "chain": "eip155:84532"
  }
}
```

### Reputation Registry Usage

| Event | Feedback call | Score logic | Evidence |
|---|---|---|---|
| Trade opened | `giveFeedback(agentId, 50, "trade_open", "BTC/USD", evidenceURI)` | Neutral start | Full proposal + risk verdict |
| Material change | `giveFeedback(agentId, score, "trade_update", pair, evidenceURI)` | Based on unrealized PnL | Updated position state |
| Trade closed | `giveFeedback(agentId, score, "trade_close", pair, evidenceURI)` | Based on realized PnL | Full decision record with outcome |
| PASS decision | `giveFeedback(agentId, 55, "no_trade", "MARKET", evidenceURI)` | Slightly positive (discipline) | Regime state + reasoning |
| Risk parameter change | `giveFeedback(agentId, 50, "risk_adjust", "RISK", evidenceURI)` | Neutral (informational) | Old params → new params + trigger |

### Validation Registry Usage (genuinely external)

| Step | Who | On-chain call | Data |
|---|---|---|---|
| 1. Strategist proposes | TrustDesk wallet | `validationRequest(riskManagerAddr, agentId, requestURI, requestHash)` | Proposal on IPFS |
| 2. Risk Manager evaluates | Risk Manager wallet (separate) | `validationResponse(requestHash, approved, responseURI, responseHash, "risk_check")` | Verdict on IPFS |
| 3. External validator (optional) | Any wallet | `TrustDeskOpenValidator.validateTrade(agentId, requestHash, opinion, reason, evidenceURI)` | External analysis |

The critical difference from v1: step 2 comes from a different wallet than step 1. On-chain, these are two distinct entities, which is what the ERC-8004 spec intends.

---

## Gas Management (Base Sepolia)

Base Sepolia is a testnet, so gas is free in theory. In practice, faucets are unreliable during high-traffic periods like hackathons. Running out of testnet ETH would silently kill the entire trust layer while the trading agent keeps running, creating a gap in the on-chain record that's worse than never having the trust layer at all.

### Pre-Funding Strategy

At setup time, fund both wallets generously:

| Wallet | Purpose | Target balance | Estimated tx count |
|---|---|---|---|
| TrustDesk agent (0xABC) | Identity registration, reputation feedback, validation requests | 0.5 ETH | ~150 txs over 14 days |
| Risk Manager (0xDEF) | Validation responses | 0.3 ETH | ~80 txs over 14 days |

### Faucet Sources (in priority order)

1. Base Sepolia faucet (base.org/faucets)
2. Alchemy Sepolia faucet (requires Alchemy account)
3. Chainlink faucet (faucets.chain.link)
4. Manual bridge from Sepolia L1 if all faucets are dry

### Gas Monitor

A background check runs every 30 minutes on both wallets. When balance drops below thresholds, the Auditor switches write priority tiers:

| Balance | Write behavior |
|---|---|
| > 0.1 ETH | **Normal.** All writes enabled: trade open, trade close, material updates, PASS summaries, risk parameter changes, validation requests/responses. |
| 0.05 - 0.1 ETH | **Reduced.** Disable PASS summaries and material update writes. Preserve: trade open, trade close, validation request/response. These are the entries judges will inspect most closely. |
| 0.01 - 0.05 ETH | **Critical.** Disable all except trade close + validation response. These two entries complete the audit trail for trades that already have an open record. |
| < 0.01 ETH | **Emergency.** Queue all writes for retry. Alert in dashboard. Attempt faucet refill automatically. |

Every priority downgrade is logged in the dashboard with a banner: "On-chain writes reduced: gas balance low. Trade execution unaffected."

The trading agent continues to operate normally at all gas levels. Gas management only affects the trust layer's write frequency, never the trading logic.

---

## Kraken CLI Integration (Revised)

### Dual-Path Connection

**Primary: MCP**
```python
# LangGraph tool definition
@tool
async def kraken_mcp(command: str, params: dict) -> dict:
    """Execute Kraken CLI command via MCP server."""
    try:
        result = await mcp_client.call_tool("kraken", command, params)
        return json.loads(result)
    except MCPConnectionError:
        logger.warning("MCP failed, falling back to subprocess")
        return await kraken_subprocess(command, params)
```

**Fallback: Subprocess**
```python
async def kraken_subprocess(command: str, params: dict) -> dict:
    """Execute Kraken CLI command via direct subprocess call."""
    args = ["kraken", command, "-o", "json"]
    for key, value in params.items():
        args.extend([f"--{key}", str(value)])

    proc = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise KrakenCLIError(stderr.decode())
    return json.loads(stdout.decode())
```

Both paths return identical JSON. The Orchestrator doesn't care which path succeeded. This eliminates the single point of failure the judge identified.

### Command Map (expanded)

| Function | Command | Frequency | Used by |
|---|---|---|---|
| Price data | `kraken ticker --pair BTCUSD` | Every 1-2 min | Signal Engine |
| Candlesticks | `kraken ohlc --pair BTCUSD --interval 15` | Every 5 min | Signal Engine |
| Order book | `kraken book --pair BTCUSD --count 25` | Every 5 min | Signal Engine |
| Recent trades | `kraken trades --pair BTCUSD` | Every 5 min | Signal Engine |
| Account balance | `kraken balance` | After every trade + every 15 min | Risk Manager |
| Open orders | `kraken order list` | After every trade + every 5 min | Orchestrator |
| Place order (paper) | `kraken paper buy --pair BTCUSD --type limit --price X --volume Y` | On trade signal | Orchestrator |
| Place order (live) | `kraken order buy --pair BTCUSD --type limit --price X --volume Y` | On trade signal | Orchestrator |
| Cancel order | `kraken order cancel --id XXXXX` | On invalidation/timeout | Orchestrator |
| Trade history | `kraken trades list` | Every 15 min | Auditor (PnL tracking) |
| WebSocket stream | `kraken ws ticker BTCUSD ETHUSD SOLUSD` | Continuous | Signal Engine (real-time) |

### Paper → Live Pipeline

The system runs in paper mode by default. Switching to live requires:

1. Set `TRUSTDESK_MODE=live` in environment.
2. Backtest must have passed go/no-go criteria.
3. Paper trading must show positive PnL over at least 24 hours.
4. Kraken API key must have trade permissions (not just read-only).

The code path is identical. Only the CLI command changes (`paper buy` → `order buy`).

---

## Tech Stack (Revised)

| Layer | Technology | Why |
|---|---|---|
| Signal Engine | **Python 3.11 + pandas + ta-lib** | Deterministic indicator calculation. ta-lib is the industry standard for technical analysis. Fast C-backed computation. |
| Agent orchestration | **LangGraph** (Python) | Multi-agent state machine. Handles the proposal → validation → execution → logging graph. |
| LLM | **Claude Sonnet 4** (via Anthropic API) | Strategist + Risk Manager reasoning. Fast structured output. |
| Kraken integration | **Kraken CLI** (Rust binary, MCP + subprocess) | Dual-path connection. MCP primary, subprocess fallback. |
| Smart contracts | **Foundry** (Solidity) | TrustDeskOpenValidator contract + any ERC-8004 wrapper logic. |
| On-chain interaction | **viem** (TypeScript) or **web3.py** (Python) | ERC-8004 registry calls from Auditor. viem preferred for type safety. |
| IPFS storage | **Pinata** | Decision Records, proposals, verdicts stored off-chain. Pinned for persistence. |
| Dashboard | **React + Tailwind + Recharts + WebSocket** | Real-time dashboard. Tiered build (see below). |
| Database | **PostgreSQL** (via Supabase or local) | Trade log, agent conversation archive, signal history, backtest results. More robust than SQLite for concurrent access. |
| Real-time comms | **WebSocket** (FastAPI) | Stream agent events to dashboard. |
| Deployment | **Railway / Fly.io** (backend) + **Vercel** (dashboard) | Persistent process for trading agent. Edge deployment for dashboard. |
| Monitoring | **Sentry + structured logging** | Error tracking. Every agent cycle logged with correlation IDs. |

---

## Dashboard Design (Tiered)

### Tier 1: MVP (Must Ship)

**The Desk Activity Feed.** This is the only panel that matters for demo impressiveness.

Full-width, real-time feed showing everything the desk processes. Color-coded by event type:
- 🟦 Blue for agent proposals (any connected agent)
- 🟥 Red/amber/green for Risk Manager verdicts (red = rejected, amber = modified, green = approved)
- 🟩 Green for Auditor confirmations (with IPFS and tx links)
- 🟨 Yellow for reputation tier changes (promotion/demotion)
- ⚪ Gray for PASS decisions

Each entry is expandable to show the full JSON payload. Collapsed view shows the one-line summary. Expanded view shows the complete proposal, risk verdict, reputation impact, and on-chain references.

Header bar showing: connected agent name + reputation tier, portfolio NAV, unrealized PnL, and a "LIVE" or "PAPER" badge.

### Tier 2: Enhanced (Should Ship)

**PnL Panel (right sidebar, 30% width)**
- Cumulative PnL line chart (Recharts, updating every minute)
- Current drawdown as a percentage (with color-coded severity: green/yellow/orange/red)
- Win/loss counter
- Today's PnL vs all-time PnL

**Reputation Panel (below PnL, same sidebar)**
- Current tier badge (Unproven / Established / Trusted) with progress toward next tier
- ERC-8004 reputation score summary (total verified trades, average score)
- Promotion/demotion history timeline
- Validation count (internal + external)
- "Verify on-chain" link to Base Sepolia explorer for agent's Identity Registry entry
- Most recent on-chain transaction hash (clickable)

### Tier 3: Stretch (Nice to Have)

**Trade Replay.** Click any completed trade in the Agent Feed to see a timeline view: proposal → validation → execution → outcome, with the Signal Engine's state at each step. Includes a mini price chart showing entry, stop, and exit levels.

**External Validator Panel.** Shows any third-party validation responses posted through the Open Validation API. Compares external opinions with the Risk Manager's verdict.

**Backtest Results.** An embedded view of the strategy's backtest performance: equity curve, drawdown chart, trade distribution by regime.

---

## Social Engagement Plan

The hackathon includes a social engagement component, and the Surge platform rewards build-in-public activity. Social presence starts on day 1.

### Content Calendar

| Day | Content | Platform |
|---|---|---|
| 1 | "Anyone can build a trading agent. Nobody can prove it won't blow up. We're building TrustDesk — a trading desk any agent can plug into." + architecture diagram | X, tag @lablabai @Surgexyz_ |
| 2 | Video: Kraken CLI paper trade working. "First trade through the desk. Risk Manager cut position size before it executed. Working as designed." | X |
| 3 | Screenshot: Reputation tier table. "Your agent starts with $100 and tight limits. Prove it won't blow up, unlock more capital. All on-chain via ERC-8004." | X |
| 5 | Video: First ERC-8004 identity registered. Show the block explorer. "TrustDesk is on-chain. Every trade, every risk verdict, every reputation change — verifiable." | X + early.surge.xyz |
| 7 | Dashboard preview showing desk activity feed. "Watch the desk in real-time: agent proposes, Risk Manager gates, trade executes, reputation updates." | X |
| 9 | Thread: "Why we built a trading desk, not a trading bot." 5-tweet breakdown: trust problem → pluggable agents → reputation = capital → ERC-8004 as product. | X |
| 11 | Live trading screenshot with PnL + reputation tier. "Day 11: Demo agent promoted to Established tier. 20+ verified trades, positive PnL, wider limits unlocked." | X + early.surge.xyz |
| 13 | Demo video teaser (30 seconds). | X, tag @lablabai @Surgexyz_ |
| 14 | Submission post. Full demo video link. Tag everyone. | X + lablab.ai |

### Content Principles

- Show real artifacts (screenshots, block explorer links, CLI output), not mockups.
- Every post should include a visual.
- Tag @lablabai and @Surgexyz_ on posts related to hackathon progress.
- Engage with other builders' posts. The hackathon community is small, mutual engagement amplifies reach.

---

## Demo Script (v3, 2 Minutes)

**[0:00-0:15] Hook**
"Anyone can build a trading agent. Nobody can prove it won't blow up. TrustDesk is a trading desk that any agent can plug into — with risk controls that prevent blowups and an on-chain reputation system that determines how much capital each agent earns."

**[0:15-0:45] How It Works**
Show architecture. "Three layers. The Strategist slot is where any agent connects — for this demo, it's Claude. The Risk Manager is a separate process with its own wallet that gates every trade against hard limits. The Auditor writes every decision to ERC-8004. Agents bring their own signals and strategy. The desk controls what happens after."

**[0:45-1:15] Live Dashboard**
Walk through a trade. "Here's a live trade. Our demo agent proposed a BTC long at 8% position size. The Risk Manager flagged correlated exposure with an existing ETH position and cut it to 5.5%. Executed in under 2 seconds via Kraken CLI. Stop placed on-exchange. Then the full decision posted to ERC-8004 — proposal, risk verdict, outcome. Both checkmarks: executed and on-chain."

**[1:15-1:35] Reputation = Capital**
Show reputation tier. "This is what makes it work. Every verified trade builds the agent's on-chain reputation. Higher reputation unlocks more capital and wider risk limits. Blow your drawdown limit? Automatic demotion — tighter limits, smaller allocation. No human in the loop. The chain is the only input."

**[1:35-1:50] On-Chain Proof**
Show Base Sepolia explorer. "Every number here is verifiable. The Risk Manager's verdicts come from a separate wallet — genuinely independent. And through our Open Validation API, anyone can post their own assessment of any trade. This isn't a self-reported backtest. It's a provable track record."

**[1:50-2:00] Close**
"TrustDesk is not a trading bot. It's the desk that makes trading bots safe to deploy with real money."

---

## Risk & Mitigation (Revised)

| Risk | Impact | Mitigation |
|---|---|---|
| LLM misinterprets signals | Bad trade proposal | Signal Engine provides pre-computed, labeled signals. Hard limits in Risk Manager catch nonsensical proposals before execution. LLM never does math. Signal Alignment Score is deterministic. |
| LLM API unavailable | Can't generate proposals or evaluate soft limits | Strategist skips cycle. Risk Manager switches to hard-limits-only mode. Hard limits are deterministic and always available. Trades flagged `APPROVED_HARD_ONLY` on-chain. Dashboard shows yellow indicator. |
| MCP connection failure | Can't reach Kraken | Subprocess fallback path. Both paths return identical JSON. Orchestrator is path-agnostic. |
| Validation latency | Stale limit orders | Dual-path validation: fast local path for sub-second execution, async trust path for on-chain record. Trade executes immediately, chain confirmation follows within 60 seconds. |
| ERC-8004 contract calls failing | Missing on-chain records | Write queue with exponential backoff retry. Dashboard shows "pending" status. Retry queue persists across restarts (PostgreSQL). |
| Testnet gas exhaustion | Trust layer stops writing | Gas monitor with tiered write priority. Critical writes (trade close, validation response) preserved longest. Pre-fund both wallets at setup. Three fallback faucet sources identified. |
| PASS logging floods registry | Dilutes reputation signal, wastes gas | Rate-limited to 1 on-chain PASS entry per hour per regime. Individual cycles batched into summaries. Regime transitions logged immediately as exceptions. |
| Flat or negative PnL | Lower leaderboard ranking | Graduated drawdown response (5 tiers, not binary). Combined track lets strong ERC-8004 implementation compensate. PASS summaries logged as evidence of discipline. |
| External validator spam | Noisy validation data | TrustDeskOpenValidator contract has no gas sponsorship. Spam costs the spammer gas. Dashboard shows external validations separately from Risk Manager verdicts. |
| Kraken CLI rate limits | Missed data or rejected orders | Kraken CLI has built-in rate limiting. Signal Engine uses longer polling intervals in passive regimes. WebSocket for real-time data reduces REST call volume. |
| Backtest overfitting | Strategy works on history but fails live | Use walk-forward validation (train on 60 days, test on 30). Rolling equity curve monotonicity test. Check per-regime PnL distribution (no single regime > 80% of total). |
| Process crash during trade | Orphaned positions | Exchange-side stop losses survive process crashes. On restart, reconcile local state with Kraken portfolio state. PostgreSQL persists all state. |
| IPFS pinning failure | Evidence URIs return 404 | Use Pinata with pin persistence. Store CIDs in PostgreSQL. Re-pin on startup if any CIDs are unreachable. |

---

## Success Metrics

### For the Hackathon

| Metric | Target | Measurement |
|---|---|---|
| Net PnL | Positive (any amount) | Kraken read-only API key verification |
| Max drawdown | < 10% | Tracked in dashboard + on-chain |
| ERC-8004 on-chain records | 30+ feedback entries, 15+ validation artifacts | Queryable via block explorer |
| Validation separation | 100% of validation responses from Risk Manager wallet (0xDEF), not agent wallet (0xABC) | On-chain address inspection |
| Fast path execution latency | < 3 seconds from proposal to order placed | Logged timestamps in dashboard |
| Trust path confirmation | 100% of executed trades have corresponding on-chain records within 5 minutes | Retry queue drain rate |
| Gas health | Both wallets above 0.05 ETH at submission time | Wallet balance check |
| Backtest passed | Go/no-go criteria met before live deployment | Backtest report in GitHub repo |
| Reputation tier progression | Demo agent promoted to Established during competition | 20+ verified trades with positive PnL |
| Demo quality | Judges can understand TrustDesk's value in < 30 seconds | Desk activity feed + reputation tier visible on first screen |
| Social engagement | 8+ build-in-public posts with artifacts | X timeline + early.surge.xyz activity |
| Submission completeness | Video, description, live dashboard link, GitHub, Kraken API key | lablab.ai submission form |

### Beyond the Hackathon

| Metric | Target | Why it matters |
|---|---|---|
| Second agent connected | At least 1 non-demo agent submits proposals through the Agent Interface | Proves the desk is genuinely pluggable, not a monolith |
| External validators | At least 1 non-team validator posts a response | Proves the Open Validation API works as intended |
| On-chain data quality | Every trade has a complete lifecycle (open → update → close) | Full reputation trail with no gaps |
| Reputation tier transition | At least 1 promotion or demotion recorded on-chain | Proves the reputation-capital mechanism works end-to-end |

---

## What Makes This Win (v3)

1. **It's a platform, not a bot.** Every other team will submit a trading agent. TrustDesk submits the infrastructure that makes *any* trading agent safe to deploy. This is a fundamentally different pitch — and a stronger business case. One bot has one strategy. A desk that any agent can plug into has a network effect.

2. **Reputation = capital access is a novel mechanism.** On-chain reputation isn't a vanity metric — it directly controls how much capital an agent can use and how wide its risk limits are. This makes ERC-8004 load-bearing, not decorative. Judges from the ERC-8004 team will immediately see this as the intended use case.

3. **The Risk Manager is genuinely external.** Separate wallet, separate process, on-chain validation from a different address. This is what ERC-8004's Validation Registry was designed for. Most teams will fake this with internal function calls.

4. **Dual-path validation is how real trading desks work.** Fast local execution + async on-chain attestation mirrors institutional compliance. It's honest about the latency tradeoff instead of pretending on-chain gating is practical at trading speed.

5. **The agent-agnostic architecture justifies why agents matter.** The desk doesn't care what's inside the black box — LLM, script, neural net. It controls what the black box can do. This sidesteps the "why do you need AI for this?" question entirely: the desk is the product, agents are the customers.

6. **Interim reputation signals solve a real problem.** The three-stage feedback lifecycle (open → update → close) means there's always on-chain data to inspect, even for in-progress trades. Rate-limited PASS summaries keep the registry clean without losing the discipline narrative.

7. **The Open Validation API is a differentiator nobody else will build.** Even if no external validators participate, the fact that the infrastructure exists and is callable shows a deeper understanding of ERC-8004's vision for open trust networks.

8. **Every failure mode has a graceful degradation path.** LLM down → hard-limits-only mode. MCP down → subprocess fallback. Gas low → tiered write priority. Process crash → exchange-side stops + state reconciliation. No single failure kills the system.

9. **The demo tells a story judges remember.** An agent proposes, the Risk Manager overrides, the trade executes, the reputation updates — all visible in real-time. The "posted from a different wallet" moment is the killer detail. The closing line lands: "It's the desk that makes trading bots safe to deploy with real money."

10. **The strategy is backtested with honest criteria.** Rolling equity curve monotonicity instead of fragile annualized Sharpe. Explicit partial-exit counting rules. Per-regime PnL distribution checks. No single-regime overfitting.
