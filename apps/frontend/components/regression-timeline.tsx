"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useRegressionHistory } from "@/lib/hooks/use-regression";

interface Props {
  projectId: string;
}

export function RegressionTimeline({ projectId }: Props) {
  const { data: history, isLoading } = useRegressionHistory(projectId);

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">로딩 중...</p>;
  }

  if (!history?.length) {
    return (
      <p className="text-sm text-muted-foreground">
        완료된 분석 세션이 없습니다.
      </p>
    );
  }

  const maxTotal = Math.max(...history.map((h) => h.total), 1);

  return (
    <div className="space-y-3">
      {history.map((entry) => (
        <Card key={entry.session_id} className="p-0">
          <CardHeader className="p-4 pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="font-mono text-xs">
                {entry.commit_sha.slice(0, 8)}
              </CardTitle>
              <span className="text-xs text-muted-foreground">
                {new Date(entry.started_at).toLocaleDateString("ko-KR")}
              </span>
            </div>
          </CardHeader>
          <CardContent className="p-4 pt-0 space-y-2">
            <div className="flex gap-2">
              <Badge variant="destructive" className="text-[10px]">
                NEW {entry.new}
              </Badge>
              <Badge variant="secondary" className="text-[10px]">
                RECURRING {entry.recurring}
              </Badge>
              <Badge variant="outline" className="text-[10px]">
                RESOLVED {entry.resolved}
              </Badge>
            </div>
            <div className="flex h-2 rounded-full overflow-hidden bg-muted">
              {entry.new > 0 && (
                <div
                  className="bg-red-500"
                  style={{ width: `${(entry.new / maxTotal) * 100}%` }}
                />
              )}
              {entry.recurring > 0 && (
                <div
                  className="bg-yellow-500"
                  style={{ width: `${(entry.recurring / maxTotal) * 100}%` }}
                />
              )}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
