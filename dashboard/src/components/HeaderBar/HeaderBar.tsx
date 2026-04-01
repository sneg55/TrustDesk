interface Props {
  tier: string;
  nav: number;
  unrealizedPnl: number;
  connected: boolean;
  mode?: "LIVE" | "PAPER";
}

const TIER_BADGES: Record<string, string> = {
  NOVICE: "bg-gray-600",
  EXPLORER: "bg-blue-600",
  STRATEGIST: "bg-purple-600",
  VETERAN: "bg-amber-600",
  ELITE: "bg-red-600",
};

export function HeaderBar({ tier, nav, unrealizedPnl, connected, mode = "PAPER" }: Props) {
  const badgeColor = TIER_BADGES[tier] ?? "bg-gray-600";
  const pnlColor = unrealizedPnl >= 0 ? "text-green-400" : "text-red-400";

  return (
    <header className="flex items-center justify-between px-6 py-3 bg-gray-900 border-b border-gray-700">
      <div className="flex items-center gap-4">
        <h1 className="text-xl font-bold text-white">TrustDesk</h1>
        <span className={`px-2 py-0.5 rounded text-xs font-semibold text-white ${badgeColor}`}>
          {tier}
        </span>
      </div>

      <div className="flex items-center gap-6 text-sm">
        <div>
          <span className="text-gray-400">NAV </span>
          <span className="text-white font-mono">${nav.toLocaleString()}</span>
        </div>
        <div>
          <span className="text-gray-400">PnL </span>
          <span className={`font-mono ${pnlColor}`}>
            {unrealizedPnl >= 0 ? "+" : ""}{unrealizedPnl.toFixed(2)}
          </span>
        </div>
        <span
          className={`px-2 py-0.5 rounded text-xs font-semibold ${
            mode === "LIVE" ? "bg-green-700 text-green-100" : "bg-yellow-700 text-yellow-100"
          }`}
        >
          {mode}
        </span>
        <span
          className={`h-2 w-2 rounded-full ${connected ? "bg-green-500" : "bg-red-500"}`}
          title={connected ? "Connected" : "Disconnected"}
        />
      </div>
    </header>
  );
}
