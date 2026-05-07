'use client';

import Link from 'next/link';
import { use } from 'react';
import { useProject } from '@/lib/hooks/use-projects';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { StatusBadge, PriorityBadge } from '@/components/status-badge';

export default function ProjectDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data: project, isLoading, error } = useProject(id);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">로딩 중...</p>
      </div>
    );
  }

  if (error) throw error;
  if (!project) return null;

  return (
    <div className="mx-auto max-w-5xl p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <Link href="/projects" className="text-sm text-muted-foreground hover:underline">
            &larr; 프로젝트 목록
          </Link>
          <h1 className="text-3xl font-bold">{project.name}</h1>
        </div>
        <div className="flex gap-2">
          <StatusBadge status={project.status} />
          <PriorityBadge priority={project.priority} />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">개요</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">GitLab</span>
              <span className="font-mono">{project.gitlab_project_id}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">마감일</span>
              <span>{project.deadline ?? '미지정'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">생성일</span>
              <span>{new Date(project.created_at).toLocaleDateString('ko-KR')}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">분석 회차</CardTitle>
          </CardHeader>
          <CardContent className="flex items-center justify-center text-muted-foreground">
            <p>아직 분석 이력이 없습니다.</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium text-muted-foreground">액션</CardTitle>
        </CardHeader>
        <CardContent>
          <Button disabled>분석 실행 (Sprint 2에서 활성화)</Button>
        </CardContent>
      </Card>
    </div>
  );
}
