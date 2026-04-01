/** Event types matching the backend EventType enum. */
export type EventType =
  | "proposal"
  | "verdict"
  | "execution"
  | "reputation_update"
  | "pass_decision"
  | "on_chain_confirmed";

/** A single event from the WebSocket stream. */
export interface TrustDeskEvent {
  type: EventType;
  data: Record<string, unknown>;
  timestamp: number;
}

/** Trade record from GET /api/trades. */
export interface Trade {
  proposal_id: string;
  pair: string;
  side: "long" | "short";
  size: number;
  status: "executed" | "rejected" | "modified" | "skipped";
  pnl: number;
  timestamp: number;
}

/** Portfolio from GET /api/portfolio. */
export interface Portfolio {
  positions: Trade[];
  nav: number;
  unrealized_pnl: number;
}

/** Reputation from GET /api/reputation. */
export interface Reputation {
  tier: string;
  score: number;
  total_trades: number;
  successful_trades: number;
  promotion_history: PromotionRecord[];
}

export interface PromotionRecord {
  from: string;
  to: string;
  timestamp: number;
}
