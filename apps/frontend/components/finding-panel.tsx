"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CommentList } from "@/components/comment-list";
import type { Finding } from "@/lib/api/findings";
import { useUpdateFindingStatus } from "@/lib/hooks/use-findings";
import { cn } from "@/lib/utils";

const SEVERITY_COLORS: Record<string, string> = {
  critical: "bg-[#ff5555] text-[#282a36]",
  high: "bg-[#ffb86c] text-[#282a36]",
  medium: "bg-[#f1fa8c] text-[#282a36]",
  low: "bg-[#8be9fd] text-[#282a36]",
  info: "bg-[#6272a4] text-[#f8f8f2]",
};

interface Props {
  findings: Finding[];
  selected: Finding | null;
  onSelect: (f: Finding) => void;
  sessionId: string;
}

export function FindingPanel({
  findings,
  selected,
  onSelect,
  sessionId,
}: Props) {
  const updateStatus = useUpdateFindingStatus(sessionId);

  const handleAction = (findingId: string, status: string) => {
    updateStatus.mutate({ findingId, status });
  };

  if (findings.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        취약점이 없습니다.
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {selected && (
        <div className="shrink-0 border-b p-4 space-y-3">
          <div className="flex items-center gap-2">
            <span
              className={cn(
                "rounded px-2 py-0.5 text-xs font-bold",
                SEVERITY_COLORS[selected.severity],
              )}
            >
              {selected.severity.toUpperCase()}
            </span>
            <Badge variant="outline">{selected.category}</Badge>
          </div>
          <h3 className="font-semibold">{selected.title}</h3>
          <p className="text-sm text-muted-foreground">
            {selected.description}
          </p>
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="destructive"
              onClick={() => handleAction(selected.id, "confirmed")}
            >
              확정 (c)
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => handleAction(selected.id, "false_positive")}
            >
              오탐 (f)
            </Button>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => handleAction(selected.id, "needs_review")}
            >
              검토 (r)
            </Button>
          </div>
          <CommentList findingId={selected.id} />
        </div>
      )}

      <div className="flex-1 overflow-y-auto">
        {findings.map((f) => (
          <button
            key={f.id}
            onClick={() => onSelect(f)}
            className={cn(
              "w-full text-left border-b px-4 py-3 hover:bg-muted/50 transition-colors",
              selected?.id === f.id && "bg-muted",
            )}
          >
            <div className="flex items-center gap-2 mb-1">
              <span
                className={cn(
                  "rounded px-1.5 py-0.5 text-[10px] font-bold",
                  SEVERITY_COLORS[f.severity],
                )}
              >
                {f.severity.toUpperCase()}
              </span>
              <span className="text-xs text-muted-foreground">
                {f.category}
              </span>
            </div>
            <p className="text-sm font-medium truncate">{f.title}</p>
            <p className="text-xs text-muted-foreground font-mono truncate">
              {f.file_path}:{f.line_start}
            </p>
          </button>
        ))}
      </div>
    </div>
  );
}
