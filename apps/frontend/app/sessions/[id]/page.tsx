"use client";

import Link from "next/link";
import { use } from "react";
import { useSession } from "@/lib/hooks/use-sessions";
import { getLogsUrl } from "@/lib/api/sessions";
import type { Session } from "@/lib/api/sessions";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LogStream } from "@/components/log-stream";
import { PhasePipeline } from "@/components/phase-pipeline";
import { StatCard } from "@/components/stat-card";

const TYPE_LABEL: Record<string, string> = {
  static_analysis: "정적 분석",
  target_discovery: "타겟 디스커버리",
  zero_day_hunting: "제로데이 헌팅",
};

const TARGET_PHASES = ["gathering", "filtering", "scoring", "shortlisting", "complete"];
const TARGET_LABELS: Record<string, string> = {
  gathering: "수집", filtering: "필터링", scoring: "스코어링", shortlisting: "숏리스트", complete: "완료",
};

const HUNTING_PHASES = ["setup", "fuzzing", "triage", "code_reading", "bypass", "cross_verify", "complete"];
const HUNTING_LABELS: Record<string, string> = {
  setup: "셋업", fuzzing: "퍼징", triage: "트리아지", code_reading: "코드 리딩",
  bypass: "우회", cross_verify: "교차 검증", complete: "완료",
};

function getPhaseConfig(session: Session) {
  if (session.session_type === "target_discovery") {
    return { order: TARGET_PHASES, labels: TARGET_LABELS };
  }
  return { order: HUNTING_PHASES, labels: HUNTING_LABELS };
}

function isHuntingSession(session: Session) {
  return session.session_type === "target_discovery" || session.session_type === "zero_day_hunting";
}

export default function SessionDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: session, isLoading, error } = useSession(id);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">로딩 중...</p>
      </div>
    );
  }

  if (error) throw error;
  if (!session) return null;

  const isActive = !["completed", "failed", "canceled"].includes(session.state);
  const logsUrl = isActive ? getLogsUrl(id) : null;

  return (
    <div className="mx-auto max-w-5xl p-6 space-y-6">
      <div className="space-y-1">
        <div className="flex items-center gap-3 text-sm text-muted-foreground">
          <Link
            href={`/projects/${session.project_id}`}
            className="hover:underline"
          >
            &larr; 프로젝트
          </Link>
          {isHuntingSession(session) && (
            <>
              <span>/</span>
              <Link href="/hunting" className="hover:underline">
                헌팅
              </Link>
            </>
          )}
        </div>
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold">
            {isHuntingSession(session) ? TYPE_LABEL[session.session_type] : "분석 회차"}
          </h1>
          <Badge
            variant={
              session.state === "completed"
                ? "secondary"
                : session.state === "failed"
                  ? "destructive"
                  : "default"
            }
          >
            {session.state}
          </Badge>
          {session.state === "completed" && (
            <Link href={`/sessions/${id}/review`}>
              <Button size="sm" variant="outline">
                검증 화면 열기
              </Button>
            </Link>
          )}
        </div>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <StatCard title="커밋" value={session.commit_sha.slice(0, 7)} />
        <StatCard title="모델" value={session.model_version} />
        <StatCard title="토큰" value={session.token_usage.toLocaleString()} />
        <StatCard title="비용" value={`$${session.cost}`} />
      </div>

      {isHuntingSession(session) && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">
              페이즈 진행
            </CardTitle>
          </CardHeader>
          <CardContent>
            <PhasePipeline
              phases={
                (session.phase_data as Record<string, unknown>)?.phases as
                  Record<string, { status: "pending" | "running" | "done" | "failed" }> ?? {}
              }
              currentPhase={session.current_phase}
              phaseOrder={getPhaseConfig(session).order}
              labels={getPhaseConfig(session).labels}
            />
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium text-muted-foreground">
            메타데이터
          </CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-y-3 gap-x-6 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">세션 ID</span>
            <span className="font-mono text-xs">{session.id}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">에이전트 ID</span>
            <span className="font-mono text-xs">
              {session.agent_id.slice(0, 8)}...
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">프리셋 ID</span>
            <span className="font-mono text-xs">
              {session.preset_id.slice(0, 8)}...
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">시작</span>
            <span>{new Date(session.started_at).toLocaleString("ko-KR")}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">완료</span>
            <span>
              {session.completed_at
                ? new Date(session.completed_at).toLocaleString("ko-KR")
                : "-"}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">컨테이너</span>
            <span className="font-mono text-xs">
              {session.container_image_sha ?? "-"}
            </span>
          </div>
        </CardContent>
      </Card>

      <LogStream url={logsUrl} />
    </div>
  );
}
