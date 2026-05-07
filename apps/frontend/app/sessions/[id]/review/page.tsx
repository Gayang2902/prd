"use client";

import { use, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useFindings } from "@/lib/hooks/use-findings";
import { useUpdateFindingStatus } from "@/lib/hooks/use-findings";
import { CodeViewer } from "@/components/code-viewer";
import { FindingFilter } from "@/components/finding-filter";
import { FindingPanel } from "@/components/finding-panel";
import { ReportExportModal } from "@/components/report-export-modal";
import type { Finding } from "@/lib/api/findings";

export default function ReviewPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id: sessionId } = use(params);
  const { data: findings, isLoading } = useFindings(sessionId);
  const [selected, setSelected] = useState<Finding | null>(null);
  const updateStatus = useUpdateFindingStatus(sessionId);

  const [severityFilter, setSeverityFilter] = useState("all");
  const [categoryFilter, setCategoryFilter] = useState("all");

  const categories = useMemo(() => {
    if (!findings) return [];
    return [...new Set(findings.map((f) => f.category))].sort();
  }, [findings]);

  const filtered = useMemo(() => {
    if (!findings) return [];
    return findings.filter((f) => {
      if (severityFilter !== "all" && f.severity !== severityFilter)
        return false;
      if (categoryFilter !== "all" && f.category !== categoryFilter)
        return false;
      return true;
    });
  }, [findings, severityFilter, categoryFilter]);

  useEffect(() => {
    if (filtered.length && !selected) {
      setSelected(filtered[0]);
    }
  }, [filtered, selected]);

  const navigate = useCallback(
    (direction: 1 | -1) => {
      if (!filtered.length || !selected) return;
      const idx = filtered.findIndex((f) => f.id === selected.id);
      const next = idx + direction;
      if (next >= 0 && next < filtered.length) {
        setSelected(filtered[next]);
      }
    },
    [filtered, selected],
  );

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement
      )
        return;
      switch (e.key) {
        case "j":
          navigate(1);
          break;
        case "k":
          navigate(-1);
          break;
        case "c":
          if (selected)
            updateStatus.mutate({
              findingId: selected.id,
              status: "confirmed",
            });
          break;
        case "f":
          if (selected)
            updateStatus.mutate({
              findingId: selected.id,
              status: "false_positive",
            });
          break;
        case "r":
          if (selected)
            updateStatus.mutate({
              findingId: selected.id,
              status: "needs_review",
            });
          break;
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [selected, navigate, updateStatus]);

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <p className="text-muted-foreground">로딩 중...</p>
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col">
      <header className="shrink-0 flex items-center justify-between border-b px-4 py-2">
        <div className="flex items-center gap-3">
          <Link
            href={`/sessions/${sessionId}`}
            className="text-sm text-muted-foreground hover:underline"
          >
            &larr; 회차 상세
          </Link>
          <span className="text-sm font-medium">
            검증: {filtered.length}/{findings?.length ?? 0}건
          </span>
          <FindingFilter
            severity={severityFilter}
            onSeverityChange={setSeverityFilter}
            category={categoryFilter}
            onCategoryChange={setCategoryFilter}
            categories={categories}
          />
        </div>
        <div className="flex items-center gap-3">
          <ReportExportModal sessionId={sessionId} />
          <span className="text-xs text-muted-foreground">
            j/k: 이동 | c: 확정 | f: 오탐 | r: 검토
          </span>
        </div>
      </header>

      <div className="flex flex-1 min-h-0">
        <div className="w-[58%] border-r">
          <CodeViewer finding={selected} />
        </div>
        <div className="w-[42%]">
          <FindingPanel
            findings={filtered}
            selected={selected}
            onSelect={setSelected}
            sessionId={sessionId}
          />
        </div>
      </div>
    </div>
  );
}
