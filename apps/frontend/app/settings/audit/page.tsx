"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useAuditLogs } from "@/lib/hooks/use-audit";

export default function AuditPage() {
  const { data: logs, isLoading } = useAuditLogs({ limit: 100 });

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold">감사 로그</h2>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium text-muted-foreground">
            최근 활동
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-sm text-muted-foreground">로딩 중...</p>
          ) : !logs?.length ? (
            <p className="text-sm text-muted-foreground">로그가 없습니다.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>시각</TableHead>
                  <TableHead>사용자</TableHead>
                  <TableHead>액션</TableHead>
                  <TableHead>리소스</TableHead>
                  <TableHead>상세</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {logs.map((log) => (
                  <TableRow key={log.id}>
                    <TableCell className="text-xs">
                      {new Date(log.created_at).toLocaleString("ko-KR")}
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      {log.user_id?.slice(0, 8) ?? "—"}
                    </TableCell>
                    <TableCell className="text-xs">{log.action}</TableCell>
                    <TableCell className="text-xs">
                      {log.resource_type}/{log.resource_id.slice(0, 8)}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground max-w-[200px] truncate">
                      {log.detail ?? "—"}
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
