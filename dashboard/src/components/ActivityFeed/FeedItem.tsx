import { useState } from "react";
import type { TrustDeskEvent } from "../../types";

const TYPE_COLORS: Record<string, string> = {
  proposal: "border-blue-500 bg-blue-950/30",
  verdict: "border-amber-500 bg-amber-950/30",
  execution: "border-green-500 bg-green-950/30",
  reputation_update: "border-yellow-500 bg-yellow-950/30",
  pass_decision: "border-gray-500 bg-gray-950/30",
  on_chain_confirmed: "border-emerald-500 bg-emerald-950/30",
};

function verdictColor(data: Record<string, unknown>): string {
  if (data.rejected) return "border-red-500 bg-red-950/30";
  if (data.modified) return "border-amber-500 bg-amber-950/30";
  return "border-green-500 bg-green-950/30";
}

function summaryLine(event: TrustDeskEvent): string {
  const d = event.data;
  switch (event.type) {
    case "proposal":
      return `New proposal: ${d.pair ?? "?"} ${d.side ?? ""} ${d.size ?? ""}`;
    case "verdict":
      return `Verdict: ${d.approved ? "APPROVED" : d.modified ? "MODIFIED" : "REJECTED"}`;
    case "execution":
      return `Execution: ${d.filled ? "FILLED" : "SKIPPED"}`;
    case "reputation_update":
      return `Tier change: ${d.from ?? "?"} → ${d.to ?? "?"}`;
    case "pass_decision":
      return `PASS: ${d.reason ?? "no opportunity"}`;
    case "on_chain_confirmed":
      return `On-chain confirmed: tx ${String(d.tx_hash ?? "").slice(0, 10)}...`;
    default:
      return event.type;
  }
}

export function FeedItem({ event }: { event: TrustDeskEvent }) {
  const [expanded, setExpanded] = useState(false);
  const colorClass =
    event.type === "verdict"
      ? verdictColor(event.data)
      : TYPE_COLORS[event.type] ?? "border-gray-500";

  const time = new Date(event.timestamp * 1000).toLocaleTimeString();

  return (
    <div
      className={`border-l-4 px-4 py-2 cursor-pointer rounded-r ${colorClass}`}
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex justify-between items-center">
        <span className="font-mono text-sm">{summaryLine(event)}</span>
        <span className="text-xs text-gray-400">{time}</span>
      </div>
      {expanded && (
        <pre className="mt-2 text-xs text-gray-300 overflow-x-auto">
          {JSON.stringify(event.data, null, 2)}
        </pre>
      )}
    </div>
  );
}
