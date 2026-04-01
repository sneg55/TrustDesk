/**
 * Low-level WebSocket helpers.
 * The useWebSocket hook uses this internally.
 */
const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export async function fetchTrades() {
  const resp = await fetch(`${BASE_URL}/api/trades`);
  return resp.json();
}

export async function fetchTrade(proposalId: string) {
  const resp = await fetch(`${BASE_URL}/api/trades/${proposalId}`);
  return resp.json();
}

export async function fetchReputation() {
  const resp = await fetch(`${BASE_URL}/api/reputation`);
  return resp.json();
}

export async function fetchPortfolio() {
  const resp = await fetch(`${BASE_URL}/api/portfolio`);
  return resp.json();
}
