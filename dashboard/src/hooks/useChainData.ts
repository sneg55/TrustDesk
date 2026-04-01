import { useEffect, useState } from "react";
import { getOnChainTier, getOnChainScore } from "../services/chain";

const AGENT_ADDRESS = import.meta.env.VITE_AGENT_ADDRESS as
  | `0x${string}`
  | undefined;

export function useChainData() {
  const [chainTier, setChainTier] = useState<string | null>(null);
  const [chainScore, setChainScore] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);

  const refresh = async () => {
    if (!AGENT_ADDRESS) return;
    setLoading(true);
    try {
      const [tier, score] = await Promise.all([
        getOnChainTier(AGENT_ADDRESS),
        getOnChainScore(AGENT_ADDRESS),
      ]);
      setChainTier(tier as string | null);
      setChainScore(score);
    } catch {
      // Silently fail — on-chain data is optional
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  return { chainTier, chainScore, loading, refresh };
}
