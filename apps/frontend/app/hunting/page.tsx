"use client";

import { useState } from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { NewHuntingDialog } from "@/components/new-hunting-dialog";
import { PhasePipeline } from "@/components/phase-pipeline";
import { useHuntingSessions } from "@/lib/hooks/use-hunting";
import { useProjects } from "@/lib/hooks/use-projects";
import { SESSION_TYPE_LABEL, getPhaseConfig } from "@/lib/constants";

const STATE_VARIANT: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  queued: "secondary",
  preparing: "outline",
  running: "default",
  post_processing: "outline",
  completed: "secondary",
  failed: "destructive",
  canceled: "destructive",
};

export default function HuntingPage() {
  const { data: projects } = useProjects();
  const [selectedProjectId, setSelectedProjectId] = useState<string>("__all__");
  const projectFilter = selectedProjectId === "__all__" ? undefined : selectedProjectId;
  const { data: sessions, isLoading } = useHuntingSessions(projectFilter);

  const projectMap = new Map((projects ?? []).map((p) => [p.id, p.name]));

  const active = sessions?.filter(
    (s) => !["completed", "failed", "canceled"].includes(s.state),
  ) ?? [];
  const finished = sessions?.filter(
    (s) => ["completed", "failed", "canceled"].includes(s.state),
  ) ?? [];

  return (
    <div className="mx-auto max-w-6xl p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <h1 className="text-3xl font-bold">헌팅</h1>
          <p className="text-sm text-muted-foreground">
            타겟 디스커버리 & 제로데이 헌팅 세션 관리
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={selectedProjectId} onValueChange={(v) => setSelectedProjectId(v ?? "__all__")}>
            <SelectTrigger className="w-48">
              <SelectValue placeholder="전체 프로젝트" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">전체 프로젝트</SelectItem>
              {(projects ?? []).map((p) => (
                <SelectItem key={p.id} value={p.id}>
                  {p.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <NewHuntingDialog />
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              진행중
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{active.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              완료
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {finished.filter((s) => s.state === "completed").length}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              전체
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{sessions?.length ?? 0}</p>
          </CardContent>
        </Card>
      </div>

      {active.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">
              진행중인 세션
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {active.map((s) => {
              const { order, labels } = getPhaseConfig(s);
              const phases = (s.phase_data as Record<string, unknown>)?.phases as
                | Record<string, { status: "pending" | "running" | "done" | "failed" }>
                | undefined;
              return (
                <Link key={s.id} href={`/sessions/${s.id}`} className="block">
                  <div className="space-y-2 rounded-lg border p-3 transition-colors hover:bg-accent/50">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs">{s.id.slice(0, 8)}</span>
                        <span className="text-xs text-muted-foreground">
                          {projectMap.get(s.project_id) ?? s.project_id.slice(0, 8)}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant="outline">
                          {SESSION_TYPE_LABEL[s.session_type] ?? s.session_type}
                        </Badge>
                        <Badge variant={STATE_VARIANT[s.state] ?? "outline"}>
                          {s.state}
                        </Badge>
                      </div>
                    </div>
                    <PhasePipeline
                      phases={phases ?? {}}
                      currentPhase={s.current_phase}
                      phaseOrder={order}
                      labels={labels}
                    />
                  </div>
                </Link>
              );
            })}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium text-muted-foreground">
            세션 이력
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-muted-foreground text-sm">로딩 중...</p>
          ) : !sessions?.length ? (
            <p className="text-muted-foreground text-sm">
              헌팅 세션이 없습니다. 위의 &quot;새 헌팅 세션&quot; 버튼으로 시작하세요.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>세션</TableHead>
                  <TableHead>프로젝트</TableHead>
                  <TableHead>유형</TableHead>
                  <TableHead>상태</TableHead>
                  <TableHead>페이즈</TableHead>
                  <TableHead>시작 시각</TableHead>
                  <TableHead>비용</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sessions.map((s) => (
                  <TableRow key={s.id} className="cursor-pointer">
                    <TableCell>
                      <Link
                        href={`/sessions/${s.id}`}
                        className="font-mono text-xs hover:underline"
                      >
                        {s.id.slice(0, 8)}
                      </Link>
                    </TableCell>
                    <TableCell className="text-xs">
                      <Link
                        href={`/projects/${s.project_id}`}
                        className="hover:underline"
                      >
                        {projectMap.get(s.project_id) ?? s.project_id.slice(0, 8)}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">
                        {SESSION_TYPE_LABEL[s.session_type] ?? s.session_type}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant={STATE_VARIANT[s.state] ?? "outline"}>
                        {s.state}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs">
                      {s.current_phase ?? "-"}
                    </TableCell>
                    <TableCell className="text-xs">
                      {new Date(s.started_at).toLocaleString("ko-KR")}
                    </TableCell>
                    <TableCell className="text-xs tabular-nums">
                      ${s.cost}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
