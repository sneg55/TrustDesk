import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { TrustDeskEvent } from "../../types";

interface Props {
  events: TrustDeskEvent[];
  nav: number;
  drawdownPct: number;
  wins: number;
  losses: number;
}

export function PnLPanel({ events, nav, drawdownPct, wins, losses }: Props) {
  // Build cumulative PnL from execution events
  const pnlData: { time: string; pnl: number }[] = [];
  let cumulative = 0;

  const executions = events
    .filter((e) => e.type === "execution" && e.data.pnl !== undefined)
    .reverse();

  for (const e of executions) {
    cumulative += Number(e.data.pnl ?? 0);
    pnlData.push({
      time: new Date((e.timestamp ?? 0) * 1000).toLocaleTimeString(),
      pnl: cumulative,
    });
  }

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg p-4">
      <h2 className="text-sm font-semibold text-gray-300 mb-3">PnL</h2>

      {pnlData.length > 0 ? (
        <ResponsiveContainer width="100%" height={160}>
          <LineChart data={pnlData}>
            <XAxis dataKey="time" tick={{ fontSize: 10 }} stroke="#6b7280" />
            <YAxis tick={{ fontSize: 10 }} stroke="#6b7280" />
            <Tooltip />
            <Line
              type="monotone"
              dataKey="pnl"
              stroke="#22c55e"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      ) : (
        <div className="text-gray-500 text-xs text-center py-6">
          No execution data yet
        </div>
      )}

      <div className="grid grid-cols-3 gap-2 mt-3 text-center text-xs">
        <div>
          <div className="text-gray-400">NAV</div>
          <div className="text-white font-mono">${nav.toLocaleString()}</div>
        </div>
        <div>
          <div className="text-gray-400">Drawdown</div>
          <div className="text-red-400 font-mono">{drawdownPct.toFixed(1)}%</div>
        </div>
        <div>
          <div className="text-gray-400">W / L</div>
          <div className="text-white font-mono">
            <span className="text-green-400">{wins}</span>
            {" / "}
            <span className="text-red-400">{losses}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
