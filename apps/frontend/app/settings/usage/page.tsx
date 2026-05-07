'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useCostSummary, useCostByProject, useCostByAgent, useDailyCost } from '@/lib/hooks/use-usage';

export default function UsagePage() {
  const { data: summary } = useCostSummary();
  const { data: byProject } = useCostByProject();
  const { data: byAgent } = useCostByAgent();
  const { data: daily } = useDailyCost();

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold">비용 대시보드</h2>

      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">총 세션</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold tabular-nums">{summary?.total_sessions ?? 0}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">총 토큰</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold tabular-nums">{(summary?.total_tokens ?? 0).toLocaleString()}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">총 비용</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold tabular-nums">${summary?.total_cost ?? '0'}</p>
          </CardContent>
        </Card>
      </div>

      {daily && daily.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">일별 비용</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-end gap-1 h-32">
              {daily.map((d) => {
                const maxCost = Math.max(...daily.map((x) => Number(x.cost)), 0.01);
                const h = (Number(d.cost) / maxCost) * 100;
                return (
                  <div key={d.date} className="flex-1 flex flex-col items-center gap-1">
                    <div
                      className="w-full bg-primary rounded-t"
                      style={{ height: `${Math.max(h, 2)}%` }}
                      title={`${d.date}: $${d.cost}`}
                    />
                    <span className="text-[9px] text-muted-foreground truncate w-full text-center">
                      {d.date.slice(5)}
                    </span>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">프로젝트별</CardTitle>
          </CardHeader>
          <CardContent>
            {byProject?.length ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>프로젝트</TableHead>
                    <TableHead>세션</TableHead>
                    <TableHead>비용</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {byProject.map((p) => (
                    <TableRow key={p.project_id}>
                      <TableCell className="font-mono text-xs">{p.project_id.slice(0, 8)}</TableCell>
                      <TableCell className="tabular-nums">{p.sessions}</TableCell>
                      <TableCell className="tabular-nums">${p.cost}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <p className="text-sm text-muted-foreground">데이터 없음</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">에이전트별</CardTitle>
          </CardHeader>
          <CardContent>
            {byAgent?.length ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>에이전트</TableHead>
                    <TableHead>세션</TableHead>
                    <TableHead>비용</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {byAgent.map((a) => (
                    <TableRow key={a.model_version}>
                      <TableCell className="text-xs">{a.model_version}</TableCell>
                      <TableCell className="tabular-nums">{a.sessions}</TableCell>
                      <TableCell className="tabular-nums">${a.cost}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <p className="text-sm text-muted-foreground">데이터 없음</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
