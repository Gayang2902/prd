'use client';

import Link from 'next/link';
import { useSessions } from '@/lib/hooks/use-sessions';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

const STATE_LABELS: Record<string, { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }> = {
  queued: { label: '대기', variant: 'outline' },
  preparing: { label: '준비중', variant: 'secondary' },
  running: { label: '실행중', variant: 'default' },
  post_processing: { label: '후처리', variant: 'secondary' },
  completed: { label: '완료', variant: 'secondary' },
  failed: { label: '실패', variant: 'destructive' },
  canceled: { label: '취소', variant: 'outline' },
};

export function SessionList({ projectId }: { projectId: string }) {
  const { data: sessions, isLoading } = useSessions(projectId);

  if (isLoading) return <p className="text-muted-foreground">로딩 중...</p>;

  if (!sessions?.length) {
    return <p className="text-center text-muted-foreground py-8">아직 분석 이력이 없습니다.</p>;
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>회차</TableHead>
          <TableHead>커밋</TableHead>
          <TableHead>상태</TableHead>
          <TableHead>모델</TableHead>
          <TableHead>토큰</TableHead>
          <TableHead>비용</TableHead>
          <TableHead>시작</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {sessions.map((s, i) => {
          const cfg = STATE_LABELS[s.state] ?? { label: s.state, variant: 'outline' as const };
          return (
            <TableRow key={s.id}>
              <TableCell>
                <Link href={`/sessions/${s.id}`} className="font-medium hover:underline">
                  #{sessions.length - i}
                </Link>
              </TableCell>
              <TableCell className="font-mono text-xs">{s.commit_sha.slice(0, 7)}</TableCell>
              <TableCell>
                <Badge variant={cfg.variant}>{cfg.label}</Badge>
              </TableCell>
              <TableCell className="text-xs">{s.model_version}</TableCell>
              <TableCell>{s.token_usage.toLocaleString()}</TableCell>
              <TableCell>${s.cost}</TableCell>
              <TableCell className="text-xs">
                {new Date(s.started_at).toLocaleString('ko-KR')}
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}
