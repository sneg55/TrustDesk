import { useEffect, useState } from "react";
import { HeaderBar } from "./components/HeaderBar";
import { ActivityFeed } from "./components/ActivityFeed";
import { PnLPanel } from "./components/PnLPanel";
import { ReputationPanel } from "./components/ReputationPanel";
import { useWebSocket } from "./hooks/useWebSocket";
import { useChainData } from "./hooks/useChainData";
import { fetchReputation, fetchPortfolio } from "./services/websocket";
import type { Reputation, Portfolio } from "./types";

export default function App() {
  const { events, connected } = useWebSocket();
  const { chainTier, chainScore, refresh: refreshChain } = useChainData();

  const [reputation, setReputation] = useState<Reputation>({
    tier: "NOVICE",
    score: 0,
    total_trades: 0,
    successful_trades: 0,
    promotion_history: [],
  });

  const [portfolio, setPortfolio] = useState<Portfolio>({
    positions: [],
    nav: 10000,
    unrealized_pnl: 0,
  });

  // Fetch initial state
  useEffect(() => {
    fetchReputation().then(setReputation).catch(() => {});
    fetchPortfolio().then(setPortfolio).catch(() => {});
  }, []);

  // Update on reputation events
  useEffect(() => {
    const latest = events.find((e) => e.type === "reputation_update");
    if (latest) {
      fetchReputation().then(setReputation).catch(() => {});
    }
  }, [events]);

  // Compute PnL stats
  const executions = events.filter((e) => e.type === "execution");
  const wins = executions.filter((e) => Number(e.data.pnl ?? 0) > 0).length;
  const losses = executions.filter((e) => Number(e.data.pnl ?? 0) < 0).length;
  const drawdownPct = portfolio.nav > 0
    ? Math.max(0, -portfolio.unrealized_pnl / portfolio.nav) * 100
    : 0;

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <HeaderBar
        tier={reputation.tier}
        nav={portfolio.nav}
        unrealizedPnl={portfolio.unrealized_pnl}
        connected={connected}
      />

      <div className="flex">
        {/* Main content — Activity Feed */}
        <main className="flex-1 p-4">
          <h2 className="text-sm font-semibold text-gray-400 mb-2">
            Activity Feed
          </h2>
          <ActivityFeed events={events} />
        </main>

        {/* Right sidebar — PnL + Reputation */}
        <aside className="w-80 p-4 space-y-4 border-l border-gray-800">
          <PnLPanel
            events={events}
            nav={portfolio.nav}
            drawdownPct={drawdownPct}
            wins={wins}
            losses={losses}
          />
          <ReputationPanel
            tier={reputation.tier}
            score={reputation.score}
            totalTrades={reputation.total_trades}
            successfulTrades={reputation.successful_trades}
            chainTier={chainTier}
            chainScore={chainScore}
            onVerify={refreshChain}
          />
        </aside>
      </div>
    </div>
  );
}
