'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePresets, useDeletePreset } from '@/lib/hooks/use-presets';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

export default function PresetsPage() {
  const { data: presets, isLoading } = usePresets();
  const deletePreset = useDeletePreset();

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">로딩 중...</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Link href="/projects" className="text-sm text-muted-foreground hover:underline">
            &larr; 프로젝트 목록
          </Link>
          <h1 className="text-2xl font-bold mt-1">프리셋 관리</h1>
        </div>
        <Link href="/presets/new">
          <Button>새 프리셋</Button>
        </Link>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>이름</TableHead>
                <TableHead>타임아웃</TableHead>
                <TableHead>재시도</TableHead>
                <TableHead>공유</TableHead>
                <TableHead className="w-24">작업</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(!presets || presets.length === 0) ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-muted-foreground py-8">
                    프리셋이 없습니다.
                  </TableCell>
                </TableRow>
              ) : (
                presets.map((p) => (
                  <TableRow key={p.id}>
                    <TableCell>
                      <Link href={`/presets/${p.id}`} className="font-medium hover:underline">
                        {p.name}
                      </Link>
                    </TableCell>
                    <TableCell>{p.timeout_seconds}s</TableCell>
                    <TableCell>{p.max_retries}회</TableCell>
                    <TableCell>
                      <Badge variant={p.is_shared ? 'default' : 'outline'}>
                        {p.is_shared ? '공유' : '개인'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => deletePreset.mutate(p.id)}
                        disabled={deletePreset.isPending}
                      >
                        삭제
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {presets && presets.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">
              프리셋 상세 — {presets[0].name}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div>
              <span className="text-muted-foreground">프롬프트 템플릿</span>
              <p className="mt-1 rounded bg-muted p-3 font-mono text-xs whitespace-pre-wrap">
                {presets[0].prompt_template || '(없음)'}
              </p>
            </div>
            <div>
              <span className="text-muted-foreground">룰셋</span>
              <pre className="mt-1 rounded bg-muted p-3 font-mono text-xs overflow-x-auto">
                {JSON.stringify(presets[0].ruleset, null, 2)}
              </pre>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
