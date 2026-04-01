interface Props {
  tier: string;
  score: number;
  totalTrades: number;
  successfulTrades: number;
  chainTier: string | null;
  chainScore: number | null;
  onVerify: () => void;
}

const TIER_ORDER = ["NOVICE", "EXPLORER", "STRATEGIST", "VETERAN", "ELITE"];

export function ReputationPanel({
  tier,
  score,
  totalTrades,
  successfulTrades,
  chainTier,
  chainScore,
  onVerify,
}: Props) {
  const tierIndex = TIER_ORDER.indexOf(tier);
  const progressPct = ((tierIndex + 1) / TIER_ORDER.length) * 100;
  const winRate = totalTrades > 0 ? ((successfulTrades / totalTrades) * 100).toFixed(1) : "0.0";

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg p-4">
      <h2 className="text-sm font-semibold text-gray-300 mb-3">Reputation</h2>

      {/* Tier progress */}
      <div className="mb-3">
        <div className="flex justify-between text-xs text-gray-400 mb-1">
          <span>{tier}</span>
          <span>{TIER_ORDER[tierIndex + 1] ?? "MAX"}</span>
        </div>
        <div className="w-full bg-gray-700 rounded-full h-2">
          <div
            className="bg-blue-500 h-2 rounded-full transition-all"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>

      {/* Score summary */}
      <div className="grid grid-cols-2 gap-2 text-xs text-center mb-3">
        <div>
          <div className="text-gray-400">Score</div>
          <div className="text-white font-mono text-lg">{score}</div>
        </div>
        <div>
          <div className="text-gray-400">Win Rate</div>
          <div className="text-white font-mono text-lg">{winRate}%</div>
        </div>
      </div>

      {/* On-chain verification */}
      <div className="border-t border-gray-700 pt-3">
        <button
          onClick={onVerify}
          className="text-xs text-blue-400 hover:text-blue-300 underline"
        >
          Verify on-chain
        </button>
        {chainTier !== null && (
          <div className="mt-1 text-xs text-gray-400">
            Chain: {chainTier} (score: {chainScore})
          </div>
        )}
      </div>
    </div>
  );
}
