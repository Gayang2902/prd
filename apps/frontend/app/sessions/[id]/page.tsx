"use client";

import Link from "next/link";
import { use } from "react";
import { useSession } from "@/lib/hooks/use-sessions";
import { getLogsUrl } from "@/lib/api/sessions";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LogStream } from "@/components/log-stream";
import { StatCard } from "@/components/stat-card";

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
        <Link
          href={`/projects/${session.project_id}`}
          className="text-sm text-muted-foreground hover:underline"
        >
          &larr; 프로젝트로 돌아가기
        </Link>
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold">분석 회차</h1>
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
