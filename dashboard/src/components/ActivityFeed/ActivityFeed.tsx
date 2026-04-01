import type { TrustDeskEvent } from "../../types";
import { FeedItem } from "./FeedItem";

interface Props {
  events: TrustDeskEvent[];
}

export function ActivityFeed({ events }: Props) {
  if (events.length === 0) {
    return (
      <div className="text-gray-500 text-center py-8">
        Waiting for events...
      </div>
    );
  }

  return (
    <div className="space-y-1">
      {events.map((event, i) => (
        <FeedItem key={`${event.timestamp}-${i}`} event={event} />
      ))}
    </div>
  );
}
