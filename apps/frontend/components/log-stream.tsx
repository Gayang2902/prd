'use client';

import { useSSE } from '@/lib/hooks/use-sse';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface Props {
  url: string | null;
}

export function LogStream({ url }: Props) {
  const { events, connected } = useSSE(url);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium">실행 로그</CardTitle>
        <Badge variant={connected ? 'default' : 'outline'}>
          {connected ? '연결됨' : '연결 안됨'}
        </Badge>
      </CardHeader>
      <CardContent>
        <div className="h-64 overflow-y-auto rounded bg-muted p-3 font-mono text-xs space-y-1">
          {events.length === 0 && (
            <p className="text-muted-foreground">로그를 기다리는 중...</p>
          )}
          {events.map((e, i) => (
            <div key={i} className="flex gap-2">
              <span className="text-muted-foreground shrink-0">
                [{new Date(e.timestamp).toLocaleTimeString('ko-KR')}]
              </span>
              <span className="text-muted-foreground shrink-0">{e.event}</span>
              <span>{e.data}</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
