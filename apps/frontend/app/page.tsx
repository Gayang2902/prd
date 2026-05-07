'use client';

import Link from 'next/link';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useCostSummary } from '@/lib/hooks/use-usage';
import { useQueue } from '@/lib/hooks/use-queue';

export default function Home() {
  const { data: cost } = useCostSummary();
  const { data: queue } = useQueue();

  const running = queue?.filter((s) => s.state === 'running').length ?? 0;
  const pending = queue?.filter((s) => s.state === 'queued').length ?? 0;

  return (
    <div className="mx-auto max-w-5xl p-6 space-y-6">
      <div className="space-y-1">
        <h1 className="text-3xl font-bold">대시보드</h1>
        <p className="text-sm text-muted-foreground">SecureScope — 사내 코드 정적 분석 플랫폼</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">총 세션</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold tabular-nums">{cost?.total_sessions ?? 0}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">총 비용</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold tabular-nums">${cost?.total_cost ?? '0'}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">실행중</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold tabular-nums">{running}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">대기중</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold tabular-nums">{pending}</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <Link href="/projects" className="block">
          <Card className="h-full hover:bg-muted/50 transition-colors">
            <CardHeader>
              <CardTitle className="text-sm">프로젝트</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground">프로젝트 목록 조회 및 분석 실행</p>
            </CardContent>
          </Card>
        </Link>
        <Link href="/queue" className="block">
          <Card className="h-full hover:bg-muted/50 transition-colors">
            <CardHeader>
              <CardTitle className="text-sm">분석 큐</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground">실행 중/대기 중 세션 모니터링</p>
            </CardContent>
          </Card>
        </Link>
        <Link href="/settings/usage" className="block">
          <Card className="h-full hover:bg-muted/50 transition-colors">
            <CardHeader>
              <CardTitle className="text-sm">비용 대시보드</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground">에이전트별/프로젝트별 비용 현황</p>
            </CardContent>
          </Card>
        </Link>
      </div>
    </div>
  );
}
