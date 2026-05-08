"use client";

import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { PriorityBadge } from "@/components/status-badge";
import { useQueue } from "@/lib/hooks/use-queue";

const TYPE_LABEL: Record<string, string> = {
  static_analysis: "정적 분석",
  target_discovery: "타겟 디스커버리",
  zero_day_hunting: "제로데이 헌팅",
};

const STATE_LABEL: Record<
  string,
  {
    label: string;
    variant: "default" | "secondary" | "destructive" | "outline";
  }
> = {
  queued: { label: "대기", variant: "secondary" },
  preparing: { label: "준비중", variant: "outline" },
  running: { label: "실행중", variant: "default" },
  post_processing: { label: "후처리", variant: "outline" },
};

export default function QueuePage() {
  const { data: sessions, isLoading } = useQueue();

  const running = sessions?.filter((s) => s.state === "running") ?? [];
  const pending =
    sessions?.filter((s) => s.state === "queued" || s.state === "preparing") ??
    [];
  const postProcessing =
    sessions?.filter((s) => s.state === "post_processing") ?? [];

  return (
    <div className="mx-auto max-w-5xl p-6 space-y-6">
      <div className="space-y-1">
        <h1 className="text-3xl font-bold">분석 큐</h1>
        <p className="text-sm text-muted-foreground">5초 간격 자동 새로고침</p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              실행중
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{running.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              대기중
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{pending.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              후처리
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{postProcessing.length}</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium text-muted-foreground">
            큐 목록
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-muted-foreground text-sm">로딩 중...</p>
          ) : !sessions?.length ? (
            <p className="text-muted-foreground text-sm">
              큐에 세션이 없습니다.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>세션</TableHead>
                  <TableHead>유형</TableHead>
                  <TableHead>상태</TableHead>
                  <TableHead>우선순위</TableHead>
                  <TableHead>모델</TableHead>
                  <TableHead>시작 시각</TableHead>
                  <TableHead>토큰</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sessions.map((s) => {
                  const stateConfig = STATE_LABEL[s.state] ?? {
                    label: s.state,
                    variant: "outline" as const,
                  };
                  return (
                    <TableRow key={s.id}>
                      <TableCell>
                        <Link
                          href={`/sessions/${s.id}`}
                          className="font-mono text-xs hover:underline"
                        >
                          {s.id.slice(0, 8)}
                        </Link>
                      </TableCell>
                      <TableCell className="text-xs">
                        {TYPE_LABEL[s.session_type] ?? s.session_type}
                      </TableCell>
                      <TableCell>
                        <Badge variant={stateConfig.variant}>
                          {stateConfig.label}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <PriorityBadge priority={s.priority} />
                      </TableCell>
                      <TableCell className="text-xs">
                        {s.model_version}
                      </TableCell>
                      <TableCell className="text-xs">
                        {new Date(s.started_at).toLocaleString("ko-KR")}
                      </TableCell>
                      <TableCell className="text-xs tabular-nums">
                        {s.token_usage.toLocaleString()}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
