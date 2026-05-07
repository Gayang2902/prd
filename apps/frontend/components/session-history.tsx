"use client";

import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useSessions } from "@/lib/hooks/use-sessions";

const STATE_LABEL: Record<string, string> = {
  queued: "대기",
  preparing: "준비중",
  running: "실행중",
  post_processing: "후처리",
  completed: "완료",
  failed: "실패",
  canceled: "취소",
};

interface Props {
  projectId: string;
}

export function SessionHistory({ projectId }: Props) {
  const { data: sessions, isLoading } = useSessions(projectId);

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">로딩 중...</p>;
  }

  if (!sessions?.length) {
    return (
      <p className="text-sm text-muted-foreground">분석 이력이 없습니다.</p>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>커밋</TableHead>
          <TableHead>상태</TableHead>
          <TableHead>모델</TableHead>
          <TableHead>토큰</TableHead>
          <TableHead>비용</TableHead>
          <TableHead>시작</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {sessions.map((s) => (
          <TableRow key={s.id}>
            <TableCell>
              <Link
                href={`/sessions/${s.id}`}
                className="font-mono text-xs hover:underline"
              >
                {s.commit_sha.slice(0, 8)}
              </Link>
            </TableCell>
            <TableCell>
              <Badge
                variant={
                  s.state === "completed"
                    ? "secondary"
                    : s.state === "failed"
                      ? "destructive"
                      : "outline"
                }
              >
                {STATE_LABEL[s.state] ?? s.state}
              </Badge>
            </TableCell>
            <TableCell className="text-xs">{s.model_version}</TableCell>
            <TableCell className="text-xs tabular-nums">
              {s.token_usage.toLocaleString()}
            </TableCell>
            <TableCell className="text-xs tabular-nums">${s.cost}</TableCell>
            <TableCell className="text-xs">
              {new Date(s.started_at).toLocaleDateString("ko-KR")}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
