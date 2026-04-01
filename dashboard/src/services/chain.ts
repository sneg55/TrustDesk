/**
 * On-chain reputation reads via viem (Base Sepolia, read-only).
 */
import { createPublicClient, http } from "viem";
import { baseSepolia } from "viem/chains";

const REPUTATION_CONTRACT = import.meta.env.VITE_REPUTATION_CONTRACT as
  | `0x${string}`
  | undefined;

const client = createPublicClient({
  chain: baseSepolia,
  transport: http(),
});

export async function getOnChainTier(agentAddress: `0x${string}`) {
  if (!REPUTATION_CONTRACT) return null;
  // ABI for getTier(address) -> string
  const tier = await client.readContract({
    address: REPUTATION_CONTRACT,
    abi: [
      {
        name: "getTier",
        type: "function",
        stateMutability: "view",
        inputs: [{ name: "agent", type: "address" }],
        outputs: [{ name: "", type: "string" }],
      },
    ],
    functionName: "getTier",
    args: [agentAddress],
  });
  return tier;
}

export async function getOnChainScore(agentAddress: `0x${string}`) {
  if (!REPUTATION_CONTRACT) return null;
  const score = await client.readContract({
    address: REPUTATION_CONTRACT,
    abi: [
      {
        name: "getScore",
        type: "function",
        stateMutability: "view",
        inputs: [{ name: "agent", type: "address" }],
        outputs: [{ name: "", type: "uint256" }],
      },
    ],
    functionName: "getScore",
    args: [agentAddress],
  });
  return Number(score);
}
