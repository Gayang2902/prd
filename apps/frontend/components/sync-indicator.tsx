"use client";

import { Badge } from "@/components/ui/badge";
import type { SyncEvent } from "@/lib/hooks/use-review-sync";
import { cn } from "@/lib/utils";

interface Props {
  connected: boolean;
  activeUsers: string[];
  lastEvent: SyncEvent | null;
}

export function SyncIndicator({ connected, activeUsers, lastEvent }: Props) {
  return (
    <div className="flex items-center gap-2">
      <span
        className={cn(
          "inline-block h-2 w-2 rounded-full",
          connected ? "bg-green-500" : "bg-red-500",
        )}
      />
      {activeUsers.length > 0 && (
        <span className="text-xs text-muted-foreground">
          {activeUsers.length}명 접속
        </span>
      )}
      {lastEvent && lastEvent.type === "finding_status_changed" && (
        <Badge variant="outline" className="text-[10px] animate-pulse">
          {lastEvent.user_id}: {lastEvent.status}
        </Badge>
      )}
    </div>
  );
}
