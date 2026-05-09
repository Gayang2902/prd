"use client";

import Link from "next/link";
import { use } from "react";
import { useSession } from "@/lib/hooks/use-sessions";
import { useFindings } from "@/lib/hooks/use-findings";
import { useTargetCandidates } from "@/lib/hooks/use-hunting";
import { useSessionLive, type AgentEvent } from "@/lib/hooks/use-session-live";
import { getLogsUrl } from "@/lib/api/sessions";
import type { Session } from "@/lib/api/sessions";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { LogStream } from "@/components/log-stream";
import { PhasePipeline } from "@/components/phase-pipeline";
import { StatCard } from "@/components/stat-card";
import { SESSION_TYPE_LABEL, getPhaseConfig } from "@/lib/constants";

function isHuntingSession(session: Session) {
  return session.session_type === "target_discovery" || session.session_type === "zero_day_hunting";
}

const SEVERITY_COLOR: Record<string, string> = {
  critical: "text-[#ff5555]",
  high: "text-[#ffb86c]",
  medium: "text-[#f1fa8c]",
  low: "text-[#8be9fd]",
  info: "text-[#6272a4]",
};

const EVENT_ICON: Record<string, string> = {
  phase_start: "▶",
  turn: "↻",
  phase_done: "✓",
  error: "✗",
};

function AgentActivityFeed({ events }: { events: AgentEvent[] }) {
  if (events.length === 0) return null;

  const lastDone = [...events].reverse().find((e) => e.event === "phase_done");

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          에이전트 활동 ({events.length}건)
        </CardTitle>
        {lastDone && (
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <span>턴: {lastDone.num_turns}</span>
            <span>비용: ${lastDone.cost_usd?.toFixed(4)}</span>
            <span>소요: {((lastDone.duration_ms ?? 0) / 1000).toFixed(1)}s</span>
          </div>
        )}
      </CardHeader>
      <CardContent>
        <div className="h-64 overflow-y-auto rounded bg-muted p-3 font-mono text-xs space-y-0.5">
          {events.map((e, i) => (
            <div key={i} className="flex gap-2">
              <span className="text-muted-foreground shrink-0 w-16">
                {new Date(e.ts).toLocaleTimeString("ko-KR")}
              </span>
              <span className="shrink-0 w-4">
                {EVENT_ICON[e.event] ?? "·"}
              </span>
              <span className="shrink-0 text-muted-foreground w-20">
                {e.phase}
              </span>
              <span>
                {e.event === "phase_start" && (
                  <span className="text-[#8be9fd]">페이즈 시작</span>
                )}
                {e.event === "turn" && (
                  <span>
                    턴 #{e.turn}
                    {e.tool_calls && e.tool_calls.length > 0 && (
                      <span className="text-[#ffb86c] ml-2">
                        [{e.tool_calls.join(", ")}]
                      </span>
                    )}
                  </span>
                )}
                {e.event === "phase_done" && (
                  <span className="text-[#50fa7b]">
                    완료 — {e.num_turns}턴, ${e.cost_usd?.toFixed(4)}, {((e.duration_ms ?? 0) / 1000).toFixed(1)}s
                  </span>
                )}
                {e.event === "error" && (
                  <span className="text-[#ff5555]">{e.message}</span>
                )}
              </span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function TargetResults({ sessionId }: { sessionId: string }) {
  const { data: targets } = useTargetCandidates(sessionId);
  if (!targets?.length) return null;
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium text-muted-foreground">
          타겟 후보 ({targets.length}건)
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>타겟</TableHead>
              <TableHead>카테고리</TableHead>
              <TableHead>심각도</TableHead>
              <TableHead>설명</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {targets.map((t) => (
              <TableRow key={t.id}>
                <TableCell className="font-mono text-xs">{t.title}</TableCell>
                <TableCell>
                  <Badge variant="outline">{t.category}</Badge>
                </TableCell>
                <TableCell>
                  <span className={SEVERITY_COLOR[t.severity] ?? ""}>
                    {t.severity}
                  </span>
                </TableCell>
                <TableCell className="text-xs max-w-xs truncate">
                  {t.description}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

function ZeroDayResults({ sessionId }: { sessionId: string }) {
  const { data: findings } = useFindings(sessionId);
  if (!findings?.length) return null;
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium text-muted-foreground">
          발견된 취약점 ({findings.length}건)
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>제목</TableHead>
              <TableHead>파일</TableHead>
              <TableHead>심각도</TableHead>
              <TableHead>카테고리</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {findings.map((f) => (
              <TableRow key={f.id}>
                <TableCell className="text-xs font-medium">{f.title}</TableCell>
                <TableCell className="font-mono text-xs">
                  {f.file_path}:{f.line_start}
                </TableCell>
                <TableCell>
                  <span className={SEVERITY_COLOR[f.severity] ?? ""}>
                    {f.severity}
                  </span>
                </TableCell>
                <TableCell>
                  <Badge variant="outline">{f.category}</Badge>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

function TraceStats({ session }: { session: Session }) {
  const pd = session.phase_data as Record<string, unknown> | null;
  const summary = pd?.results_summary as Record<string, unknown> | undefined;
  if (!summary) return null;

  const phases = (summary.phases_completed as string[]) ?? [];
  const traceEntries = phases
    .map((p) => {
      const t = summary[`${p}_trace`] as Record<string, number> | undefined;
      return t ? { phase: p, ...t } : null;
    })
    .filter(Boolean) as Array<{ phase: string; num_turns: number; cost_usd: number; duration_ms: number; tool_calls_count: number }>;

  if (traceEntries.length === 0) return null;

  const totalCost = traceEntries.reduce((s, t) => s + (t.cost_usd ?? 0), 0);
  const totalTurns = traceEntries.reduce((s, t) => s + (t.num_turns ?? 0), 0);
  const totalTools = traceEntries.reduce((s, t) => s + (t.tool_calls_count ?? 0), 0);
  const totalDuration = traceEntries.reduce((s, t) => s + (t.duration_ms ?? 0), 0);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium text-muted-foreground">
          실행 트레이스
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-4 gap-4 text-sm">
          <div>
            <span className="text-muted-foreground">총 턴</span>
            <p className="text-lg font-bold tabular-nums">{totalTurns}</p>
          </div>
          <div>
            <span className="text-muted-foreground">도구 호출</span>
            <p className="text-lg font-bold tabular-nums">{totalTools}</p>
          </div>
          <div>
            <span className="text-muted-foreground">총 비용</span>
            <p className="text-lg font-bold tabular-nums">${totalCost.toFixed(4)}</p>
          </div>
          <div>
            <span className="text-muted-foreground">총 소요</span>
            <p className="text-lg font-bold tabular-nums">{(totalDuration / 1000).toFixed(1)}s</p>
          </div>
        </div>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>페이즈</TableHead>
              <TableHead>턴</TableHead>
              <TableHead>도구 호출</TableHead>
              <TableHead>비용</TableHead>
              <TableHead>소요 시간</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {traceEntries.map((t) => (
              <TableRow key={t.phase}>
                <TableCell className="text-xs font-medium">{t.phase}</TableCell>
                <TableCell className="text-xs tabular-nums">{t.num_turns}</TableCell>
                <TableCell className="text-xs tabular-nums">{t.tool_calls_count}</TableCell>
                <TableCell className="text-xs tabular-nums">${t.cost_usd.toFixed(4)}</TableCell>
                <TableCell className="text-xs tabular-nums">{(t.duration_ms / 1000).toFixed(1)}s</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

export default function SessionDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: session, isLoading, error } = useSession(id);
  const { agentEvents } = useSessionLive(id);

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
  const logsUrl = isActive && !isHuntingSession(session) ? getLogsUrl(id) : null;

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
            {isHuntingSession(session) ? SESSION_TYPE_LABEL[session.session_type] : "분석 회차"}
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
        {isHuntingSession(session) ? (
          <>
            <StatCard
              title="현재 페이즈"
              value={
                session.current_phase
                  ? (getPhaseConfig(session).labels[session.current_phase] ?? session.current_phase)
                  : "-"
              }
            />
            <StatCard
              title="소요 시간"
              value={
                session.started_at
                  ? `${((Date.now() - new Date(session.started_at).getTime()) / 1000 / 60).toFixed(1)}분`
                  : "-"
              }
            />
          </>
        ) : (
          <>
            <StatCard title="커밋" value={session.commit_sha.slice(0, 7)} />
            <StatCard title="모델" value={session.model_version} />
          </>
        )}
        <StatCard title="턴" value={session.token_usage.toLocaleString()} />
        <StatCard title="비용" value={`$${Number(session.cost).toFixed(4)}`} />
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

      {isHuntingSession(session) && agentEvents.length > 0 && (
        <AgentActivityFeed events={agentEvents} />
      )}

      {isHuntingSession(session) && !isActive && (
        <TraceStats session={session} />
      )}

      {session.session_type === "target_discovery" && (
        <TargetResults sessionId={id} />
      )}
      {session.session_type === "zero_day_hunting" && (
        <ZeroDayResults sessionId={id} />
      )}

      {logsUrl && <LogStream url={logsUrl} />}
    </div>
  );
}
