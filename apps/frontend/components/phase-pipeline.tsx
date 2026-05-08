"use client";

import { cn } from "@/lib/utils";

interface PhaseInfo {
  status: "pending" | "running" | "done" | "failed";
}

interface Props {
  phases: Record<string, PhaseInfo>;
  currentPhase: string | null;
  phaseOrder: string[];
  labels?: Record<string, string>;
}

const STATUS_STYLES: Record<string, string> = {
  pending: "border-[#6272a4] text-[#6272a4]",
  running: "border-[#bd93f9] bg-[#bd93f9]/20 text-[#bd93f9] animate-pulse",
  done: "border-[#50fa7b] bg-[#50fa7b]/20 text-[#50fa7b]",
  failed: "border-[#ff5555] bg-[#ff5555]/20 text-[#ff5555]",
};

export function PhasePipeline({ phases, currentPhase, phaseOrder, labels }: Props) {
  return (
    <div className="flex items-center gap-1">
      {phaseOrder.map((phase, i) => {
        const info = phases[phase];
        const status = info?.status ?? "pending";
        const label = labels?.[phase] ?? phase;
        const isCurrent = phase === currentPhase;
        return (
          <div key={phase} className="flex items-center gap-1">
            {i > 0 && (
              <div
                className={cn(
                  "h-px w-4",
                  status === "done" ? "bg-[#50fa7b]" : "bg-[#6272a4]",
                )}
              />
            )}
            <div
              className={cn(
                "rounded-md border px-2 py-1 text-xs font-medium whitespace-nowrap",
                STATUS_STYLES[status],
                isCurrent && "ring-1 ring-[#bd93f9]",
              )}
            >
              {label}
            </div>
          </div>
        );
      })}
    </div>
  );
}
