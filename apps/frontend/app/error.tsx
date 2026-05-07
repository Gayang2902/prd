'use client';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      <Card className="max-w-md w-full">
        <CardHeader>
          <CardTitle className="text-destructive">오류 발생</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            페이지를 불러오는 중 오류가 발생했습니다.
          </p>
          <pre className="text-xs bg-muted p-3 rounded overflow-auto max-h-32">
            {error.message}
          </pre>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={reset}>
              다시 시도
            </Button>
            <Button variant="ghost" size="sm" onClick={() => (window.location.href = '/')}>
              홈으로
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
